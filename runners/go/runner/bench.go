package runner

import (
	"math"
	"runtime"
	"slices"
	"time"
)

// memoryMetric is allocation volume, like the JVM's: the growth of runtime.MemStats.TotalAlloc
// over one separate call (docs/specs/performance-analysis.md#measurement).
const memoryMetric = "total_alloc_delta"

// cvWindow: warmup is settled when the coefficient of variation of the latest runs is low enough.
const cvWindow = 5

// Bench mode (docs/specs/runners.md#bench-mode). Per size, in request order: each target makes
// one check call, run like a test case, whose output is reported for output targets; warmup
// samples follow until the timings settle; then the timed repetitions take turns across
// targets; then each target's memory is measured once. Every call, or batch of calls, is
// announced with bench_start first, so the CLI can attribute a hang.
//
// A sample makes `calls` back-to-back calls, each on its own freshly decoded input. Decoding and
// runtime.GC() happen outside the timed region, and results stay referenced until it ends.

type benchRun struct {
	job      *job
	settings benchSettings
	events   *writer
}

type benchCode struct {
	spec  *benchTarget
	code  caseRunner
	calls int
	// perCallNS are the timed repetitions at the current size.
	perCallNS []int64
}

func runBenchJobs(l *loader, jobs []job, events *writer) {
	for i := range jobs {
		j := &jobs[i]
		events.jobStart(j.JobID)
		run := &benchRun{job: j, settings: j.Settings, events: events}
		run.run(run.load(l))
		events.jobEnd(j.JobID)
	}
}

func (b *benchRun) load(l *loader) []*benchCode {
	var loaded []*benchCode
	for i := range b.job.Targets {
		spec := &b.job.Targets[i]
		code, failure := l.bind(spec.Target, spec.Names, &b.job.Signature)
		if failure != nil {
			b.events.targetLoadError(b.job.JobID, spec.TargetID, failure)
			continue
		}
		loaded = append(loaded, &benchCode{spec: spec, code: code})
	}
	return loaded
}

func (b *benchRun) run(targets []*benchCode) {
	active := targets
	for i := range b.job.Inputs {
		input := &b.job.Inputs[i]
		active = keep(active, func(target *benchCode) bool { return b.warmUp(target, input) })
		active = b.repetitions(active, input)
		if b.settings.Memory {
			active = keep(active, func(target *benchCode) bool { return b.memory(target, input) })
		}
	}
}

func keep(targets []*benchCode, ok func(*benchCode) bool) []*benchCode {
	var kept []*benchCode
	for _, target := range targets {
		if ok(target) {
			kept = append(kept, target)
		}
	}
	return kept
}

// warmUp makes the check call and the warmup samples; false once the target is dropped.
func (b *benchRun) warmUp(target *benchCode, input *benchInput) bool {
	point := b.start(target, input)
	result := target.code.run(&input.callInput)
	if result.status != statusOK {
		b.events.benchError(point, result)
		return false
	}
	if target.spec.Output {
		b.events.benchOutput(point, result.output)
	}
	if b.overBudget(point, result.durationNS) {
		return false
	}
	target.calls = b.batch(input, 1, result.durationNS)
	target.perCallNS = nil
	runs := []int64{result.durationNS}
	started := time.Now()
	for !b.settled(runs) && time.Since(started).Nanoseconds() < b.budgetNS() {
		s, ok := b.sample(target, input)
		if !ok || b.overBudget(b.point(target, input), s.perCallNS()) {
			return false
		}
		runs = append(runs, s.perCallNS())
		target.calls = b.batch(input, target.calls, s.wallNS)
	}
	return true
}

func (b *benchRun) repetitions(active []*benchCode, input *benchInput) []*benchCode {
	remaining := slices.Clone(active)
	for rep := 1; rep <= b.settings.Reps; rep++ {
		for _, target := range slices.Clone(remaining) {
			s, ok := b.sample(target, input)
			point := b.point(target, input)
			if !ok || b.overBudget(point, s.perCallNS()) {
				remaining = slices.DeleteFunc(remaining, func(t *benchCode) bool { return t == target })
				continue
			}
			b.events.benchSample(point, rep, s)
			target.perCallNS = append(target.perCallNS, s.perCallNS())
		}
	}
	return remaining
}

// memory measures one call's allocation volume; false when that call fails.
func (b *benchRun) memory(target *benchCode, input *benchInput) bool {
	point := b.start(target, input)
	call, ok := b.prepared(target, input, point)
	if !ok {
		return false
	}
	runtime.GC()
	var before, after runtime.MemStats
	runtime.ReadMemStats(&before)
	_, failure, _ := b.timed(target, []func() any{call})
	runtime.ReadMemStats(&after)
	if failure != nil {
		b.events.benchError(point, raised(failure, 0))
		return false
	}
	b.events.benchMemory(point, memoryMetric, after.TotalAlloc-before.TotalAlloc)
	return true
}

// sample is one timed sample; false (after bench_error) when the code fails.
func (b *benchRun) sample(target *benchCode, input *benchInput) (sample, bool) {
	point := b.start(target, input)
	prepared := make([]func() any, 0, target.calls)
	for range target.calls {
		call, ok := b.prepared(target, input, point)
		if !ok {
			return sample{}, false
		}
		prepared = append(prepared, call)
	}
	runtime.GC()
	cpuStarted := cpuNS()
	results, failure, wallNS := b.timed(target, prepared)
	cpu := cpuNS() - cpuStarted
	runtime.KeepAlive(results)
	if failure != nil {
		b.events.benchError(point, raised(failure, wallNS))
		return sample{}, false
	}
	return sample{wallNS: wallNS, cpuNS: cpu, calls: len(prepared)}, true
}

// timed makes the calls back to back; a panic ends the sample with the user's frames.
func (b *benchRun) timed(target *benchCode, calls []func() any) (results []any, failure *userError, wallNS int64) {
	results = make([]any, 0, len(calls))
	started := time.Now()
	defer func() {
		wallNS = time.Since(started).Nanoseconds()
		if recovered := recover(); recovered != nil {
			failure = describePanic(recovered, target.code.userPackage())
		}
	}()
	for _, call := range calls {
		results = append(results, call())
	}
	return results, nil, 0
}

func (b *benchRun) prepared(target *benchCode, input *benchInput, point benchPoint) (func() any, bool) {
	call, err := target.code.prepare(&input.callInput)
	if err != nil {
		b.events.benchError(point, raised(inputFailure(err), 0))
		return nil, false
	}
	return call, true
}

func (b *benchRun) settled(runs []int64) bool {
	w := b.settings.Warmup
	if len(runs) >= w.Max {
		return true
	}
	if len(runs) < w.Min {
		return false
	}
	latest := runs[max(0, len(runs)-cvWindow):]
	return len(latest) > 1 && coefficientOfVariation(latest) <= w.CV
}

// batch is the number of calls per sample so that one sample lasts at least min_sample_ns.
func (b *benchRun) batch(input *benchInput, calls int, sampleNS int64) int {
	if sampleNS >= b.settings.MinSampleNS {
		return calls
	}
	wanted := int(math.Ceil(float64(calls) * float64(b.settings.MinSampleNS) / float64(max(sampleNS, 1))))
	return max(calls, min(wanted, input.MaxBatch))
}

func (b *benchRun) overBudget(point benchPoint, perCallNS int64) bool {
	if perCallNS <= b.budgetNS() {
		return false
	}
	b.events.benchBudgetExceeded(point, perCallNS)
	return true
}

func (b *benchRun) budgetNS() int64 { return b.settings.BudgetMS * int64(time.Millisecond) }

func (b *benchRun) start(target *benchCode, input *benchInput) benchPoint {
	point := b.point(target, input)
	b.events.benchStart(point)
	return point
}

func (b *benchRun) point(target *benchCode, input *benchInput) benchPoint {
	return benchPoint{jobID: b.job.JobID, targetID: target.spec.TargetID, size: input.Size}
}

func coefficientOfVariation(values []int64) float64 {
	var sum float64
	for _, value := range values {
		sum += float64(value)
	}
	mean := sum / float64(len(values))
	if mean == 0 {
		return 0
	}
	var squares float64
	for _, value := range values {
		squares += (float64(value) - mean) * (float64(value) - mean)
	}
	return math.Sqrt(squares/float64(len(values))) / mean
}
