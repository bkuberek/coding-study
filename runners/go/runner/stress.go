package runner

import (
	"encoding/json"
	"fmt"
	"math/rand/v2"
	"reflect"
	"runtime"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// A stress run of a concurrent job (docs/specs/runners.md#run-procedure).
//
// Every run is independent: fresh argument decoding, a fresh instance, fresh probe sections and
// fresh PRNGs. Setup runs on the case goroutine; the workers are goroutines that wait at a start
// gate and are released together; the coordinator waits until every worker finished, one
// failed, or the deadline passed, then runs the final script. Go cannot stop a goroutine: after
// a failure or a stall the workers stop at their next op boundary, a worker stuck in user code
// keeps running, and the runner asks for a restart when one still runs shortly after.

const (
	phaseSetup     = "setup"
	phaseWorker    = "worker"
	phaseFinal     = "final"
	harnessPrefix  = "@"
	prngMultiplier = 1_000_003
	// leftoverGrace is how long the workers of a finished run get to return.
	leftoverGrace = 200 * time.Millisecond
	noWorker      = -1
)

// stressOp is one decoded op: the constructor, a method call, or a harness op (call nil).
type stressOp struct {
	name   string
	args   []json.RawMessage
	call   *boundCall
	method int
}

// stressFailure is a failed op: a panic (err) or an unserializable result (reason), and where.
type stressFailure struct {
	err     *userError
	reason  string
	phase   string
	opIndex int
	worker  int
}

func (f *stressFailure) at(phase string, opIndex, worker int) *stressFailure {
	f.phase, f.opIndex, f.worker = phase, opIndex, worker
	return f
}

// outcome is the run's case result; progress lists the unfinished workers of a worker failure.
func (f *stressFailure) outcome(durationNS int64, progress []workerProgress) outcome {
	result := invalid(f.reason, durationNS)
	if f.err != nil {
		result = raised(f.err, durationNS)
	}
	result.stress = &stressFields{phase: f.phase, opIndex: f.opIndex, worker: f.worker, progress: progress}
	return result
}

func stalled(progress []workerProgress, durationNS int64) outcome {
	return outcome{status: statusStalled, opIndex: -1, durationNS: durationNS,
		stress: &stressFields{progress: progress}}
}

// stressOutput is the output of a completed run: one result per op, null for void and harness
// ops.
type stressOutput struct {
	Setup   []any   `json:"setup"`
	Workers [][]any `json:"workers"`
	Final   []any   `json:"final"`
}

type stressRun struct {
	target   *classTarget
	spec     *stressCase
	sections *sections
	instance reflect.Value

	// Written by each worker, read by the coordinator once the worker finished or the run ended.
	outputs   [][]any
	completed []atomic.Int64
	inOp      []atomic.Bool
	// exited is closed when a worker's goroutine returns, however it returns.
	exited  []chan struct{}
	stopped atomic.Bool

	mu            sync.Mutex
	finished      []bool
	finishedCount int
	failure       *stressFailure
	// decided is closed when every worker finished or the first one failed.
	decided   chan struct{}
	isDecided bool
}

func newStressRun(target *classTarget, spec *stressCase) *stressRun {
	workers := len(spec.Workers)
	return &stressRun{
		target:    target,
		spec:      spec,
		sections:  &sections{counters: map[string]*sectionCounter{}},
		outputs:   make([][]any, workers),
		completed: make([]atomic.Int64, workers),
		inOp:      make([]atomic.Bool, workers),
		finished:  make([]bool, workers),
		decided:   make(chan struct{}),
	}
}

// captured runs the stress case with what its code prints captured: one buffer for the run,
// shared by every worker.
func (r *stressRun) captured() outcome {
	output := startCapture()
	result := r.run()
	result.stdout = output.stop()
	return result
}

func (r *stressRun) run() outcome {
	freshDecimalSettings()
	setup, workers, final, failure := r.decode()
	if failure != nil {
		return failure.outcome(0, []workerProgress{})
	}
	setupOutputs, failure := r.sequence(setup, phaseSetup)
	if failure != nil {
		return failure.outcome(0, nil)
	}
	started := r.startWorkers(workers)
	r.await(started)
	durationNS := time.Since(started).Nanoseconds()
	r.mu.Lock()
	r.stopped.Store(true)
	failure, allFinished := r.failure, r.finishedCount == len(workers)
	r.mu.Unlock()
	if failure != nil {
		return failure.outcome(durationNS, r.unfinished())
	}
	if !allFinished {
		return stalled(r.unfinished(), durationNS)
	}
	finalOutputs, failure := r.sequence(final, phaseFinal)
	if failure != nil {
		return failure.outcome(durationNS, nil)
	}
	result := returned(stressOutput{setupOutputs, r.outputs, finalOutputs}, durationNS)
	result.stress = &stressFields{sections: r.sections.snapshot()}
	return result
}

// decode is step 1: every argument of setup, workers and final decoded before anything runs.
func (r *stressRun) decode() (setup []stressOp, workers [][]stressOp, final []stressOp, failure *stressFailure) {
	if setup, failure = r.ops(r.spec.Setup, phaseSetup, noWorker); failure != nil {
		return nil, nil, nil, failure
	}
	for ordinal, worker := range r.spec.Workers {
		ops, failure := r.ops(worker, phaseWorker, ordinal)
		if failure != nil {
			return nil, nil, nil, failure
		}
		workers = append(workers, ops)
	}
	if r.spec.Final != nil {
		if final, failure = r.ops(*r.spec.Final, phaseFinal, noWorker); failure != nil {
			return nil, nil, nil, failure
		}
	}
	return setup, workers, final, nil
}

func (r *stressRun) ops(s script, phase string, worker int) ([]stressOp, *stressFailure) {
	if len(s.Ops) != len(s.Args) {
		err := fmt.Errorf("%d operations but %d argument lists", len(s.Ops), len(s.Args))
		return nil, (&stressFailure{err: inputFailure(err)}).at(phase, 0, worker)
	}
	ops := make([]stressOp, 0, len(s.Ops))
	for index, name := range s.Ops {
		constructs := phase == phaseSetup && index == constructorOp
		op := stressOp{name: name, args: s.Args[index]}
		if !constructs && strings.HasPrefix(name, harnessPrefix) {
			ops = append(ops, op)
			continue
		}
		m, err := r.member(name, constructs)
		if err == nil {
			op.call, err = bindPositional(m, s.Args[index])
		}
		if err != nil {
			return nil, (&stressFailure{err: inputFailure(err)}).at(phase, index, worker)
		}
		if !constructs {
			op.method = r.target.methods[name].index
		}
		ops = append(ops, op)
	}
	return ops, nil
}

// member is the constructor that starts the setup, or a declared method anywhere else.
func (r *stressRun) member(name string, constructs bool) (*checkedMember, error) {
	if constructs {
		return r.target.member(constructorOp, name)
	}
	method, ok := r.target.methods[name]
	if !ok {
		return nil, fmt.Errorf("unknown operation %q", name)
	}
	return method.call, nil
}

// sequence runs the setup (which constructs the instance) or the final script on the case
// goroutine.
func (r *stressRun) sequence(ops []stressOp, phase string) ([]any, *stressFailure) {
	outputs := []any{}
	harness := newWorkerHarness(r.sections)
	for index, op := range ops {
		if phase == phaseSetup && index == constructorOp {
			timed := invoke(r.target.constructor, op.call.args, r.target.pkg)
			if timed.failure != nil {
				return nil, (&stressFailure{err: timed.failure}).at(phase, index, noWorker)
			}
			r.instance = addressable(timed.results[0])
			outputs = append(outputs, nil)
			continue
		}
		value, failure := r.execute(op, harness)
		if failure != nil {
			return nil, failure.at(phase, index, noWorker)
		}
		outputs = append(outputs, value)
	}
	return outputs, nil
}

// execute runs one op and encodes its result at once; a harness op has no result.
func (r *stressRun) execute(op stressOp, harness *workerHarness) (any, *stressFailure) {
	if op.call == nil {
		if err := harness.run(op.name, op.args); err != nil {
			return nil, &stressFailure{err: &userError{Type: "HarnessError", Message: err.Error()}}
		}
		return nil, nil
	}
	timed := invoke(r.instance.Method(op.method), op.call.args, r.target.pkg)
	if timed.failure != nil {
		return nil, &stressFailure{err: timed.failure}
	}
	encoded, err := op.call.encodeResult(timed.results)
	if err != nil {
		return nil, &stressFailure{reason: err.Error()}
	}
	return encoded, nil
}

// startWorkers starts one goroutine per worker, waits until each waits at the gate, and opens
// it; the run's clock starts then.
func (r *stressRun) startWorkers(workers [][]stressOp) time.Time {
	var ready sync.WaitGroup
	gate := make(chan struct{})
	r.exited = make([]chan struct{}, len(workers))
	ready.Add(len(workers))
	for ordinal, ops := range workers {
		r.outputs[ordinal] = make([]any, len(ops))
		r.exited[ordinal] = make(chan struct{})
		go r.work(ordinal, ops, &ready, gate)
	}
	ready.Wait()
	if len(workers) == 0 {
		r.mu.Lock()
		r.decide()
		r.mu.Unlock()
	}
	started := time.Now()
	close(gate)
	return started
}

func (r *stressRun) work(ordinal int, ops []stressOp, ready *sync.WaitGroup, gate <-chan struct{}) {
	defer close(r.exited[ordinal])
	random := rand.New(rand.NewPCG(uint64(r.spec.Seed*prngMultiplier+int64(ordinal)), 0))
	perturb := r.spec.Perturb
	harness := newWorkerHarness(r.sections)
	ready.Done()
	<-gate
	for index, op := range ops {
		if r.stopped.Load() {
			return
		}
		if random.Float64() < perturb.YieldProbability {
			yieldTimes(1 + random.IntN(max(perturb.MaxYields, 1)))
		}
		r.inOp[ordinal].Store(true)
		value, failure := r.execute(op, harness)
		if failure != nil {
			r.fail(failure.at(phaseWorker, index, ordinal))
			return
		}
		r.outputs[ordinal][index] = value
		r.completed[ordinal].Store(int64(index + 1))
		r.inOp[ordinal].Store(false)
	}
	r.finish(ordinal)
}

// await returns when every worker finished, one failed, or the deadline passed.
func (r *stressRun) await(started time.Time) {
	deadline := started.Add(time.Duration(r.spec.DeadlineMS) * time.Millisecond)
	timer := time.NewTimer(time.Until(deadline))
	defer timer.Stop()
	select {
	case <-r.decided:
	case <-timer.C:
	}
}

func (r *stressRun) finish(ordinal int) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.finished[ordinal] = true
	r.finishedCount++
	if r.finishedCount == len(r.finished) {
		r.decide()
	}
}

// fail records the first failure; one reported after the coordinator decided is dropped.
func (r *stressRun) fail(failure *stressFailure) {
	r.mu.Lock()
	defer r.mu.Unlock()
	if r.failure == nil && !r.stopped.Load() {
		r.failure = failure
	}
	r.decide()
}

// decide wakes the coordinator; mu is held.
func (r *stressRun) decide() {
	if !r.isDecided {
		r.isDecided = true
		close(r.decided)
	}
}

// unfinished is the progress of every worker that did not finish, the failing one included.
func (r *stressRun) unfinished() []workerProgress {
	r.mu.Lock()
	defer r.mu.Unlock()
	progress := []workerProgress{}
	for worker, done := range r.finished {
		if !done {
			progress = append(progress, workerProgress{worker, int(r.completed[worker].Load()), r.inOp[worker].Load()})
		}
	}
	return progress
}

// leftovers counts the worker goroutines still running after a short grace period.
func (r *stressRun) leftovers() int {
	expired := make(chan struct{})
	timer := time.AfterFunc(leftoverGrace, func() { close(expired) })
	defer timer.Stop()
	running := 0
	for _, exited := range r.exited {
		select {
		case <-exited:
			continue
		case <-expired:
		}
		select {
		case <-exited:
		default:
			running++
		}
	}
	return running
}

func yieldTimes(count int) {
	for range count {
		runtime.Gosched()
	}
}

const (
	enterOp       = "@enter"
	exitOp        = "@exit"
	pauseOp       = "@pause"
	exclusiveMode = "exclusive"
	sharedMode    = "shared"
)

// sections are one run's probe sections, created on first use (docs/specs/runners.md#harness-
// ops).
type sections struct {
	mu       sync.Mutex
	counters map[string]*sectionCounter
}

type sectionCounter struct {
	shared, exclusive int
	counts            sectionCounts
}

func (s *sections) enter(name string, exclusive bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	c := s.counters[name]
	if c == nil {
		c = &sectionCounter{}
		s.counters[name] = c
	}
	if exclusive {
		if c.shared+c.exclusive > 0 {
			c.counts.Violations++
		}
		c.exclusive++
	} else {
		if c.exclusive > 0 {
			c.counts.Violations++
		}
		c.shared++
	}
	c.counts.Entries++
	c.counts.MaxOccupancy = max(c.counts.MaxOccupancy, c.shared+c.exclusive)
}

func (s *sections) exit(name string, exclusive bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if exclusive {
		s.counters[name].exclusive--
	} else {
		s.counters[name].shared--
	}
}

func (s *sections) snapshot() map[string]sectionCounts {
	s.mu.Lock()
	defer s.mu.Unlock()
	snapshot := make(map[string]sectionCounts, len(s.counters))
	for name, c := range s.counters {
		snapshot[name] = c.counts
	}
	return snapshot
}

// workerHarness runs one worker's harness ops; it remembers the mode of each section the
// worker is inside, last entered last.
type workerHarness struct {
	sections *sections
	entered  map[string][]bool
}

func newWorkerHarness(s *sections) *workerHarness {
	return &workerHarness{sections: s, entered: map[string][]bool{}}
}

func (h *workerHarness) run(op string, args []json.RawMessage) error {
	switch {
	case op == enterOp && len(args) == 2:
		name, named := jsonString(args[0])
		mode, moded := jsonString(args[1])
		if named && moded && (mode == exclusiveMode || mode == sharedMode) {
			exclusive := mode == exclusiveMode
			h.sections.enter(name, exclusive)
			h.entered[name] = append(h.entered[name], exclusive)
			return nil
		}
	case op == exitOp && len(args) == 1:
		if name, ok := jsonString(args[0]); ok {
			modes := h.entered[name]
			if len(modes) == 0 {
				return fmt.Errorf("%s %q without a matching %s", exitOp, name, enterOp)
			}
			h.entered[name] = modes[:len(modes)-1]
			h.sections.exit(name, modes[len(modes)-1])
			return nil
		}
	case op == pauseOp && len(args) == 1:
		var count int
		if json.Unmarshal(args[0], &count) == nil {
			yieldTimes(count)
			return nil
		}
	}
	raw := make([]string, len(args))
	for i, arg := range args {
		raw[i] = string(arg)
	}
	return fmt.Errorf("%s cannot take [%s]", op, strings.Join(raw, ","))
}

func jsonString(raw json.RawMessage) (string, bool) {
	var text string
	return text, json.Unmarshal(raw, &text) == nil
}
