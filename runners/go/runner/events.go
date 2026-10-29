package runner

import (
	"bytes"
	"encoding/json"
	"io"
	"runtime"
	"strings"
)

const runnerName = "go"

// field keeps event keys in the order the spec shows them.
type field struct {
	key   string
	value any
}

// writer writes the JSON Lines event stream. Each line is one unbuffered write, so the CLI sees
// it as soon as it is written (docs/specs/runners.md#event-stream).
type writer struct{ out io.Writer }

func (w *writer) emit(fields ...field) {
	var line bytes.Buffer
	line.WriteByte('{')
	for i, f := range fields {
		if i > 0 {
			line.WriteByte(',')
		}
		line.Write(marshal(f.key))
		line.WriteByte(':')
		line.Write(marshal(f.value))
	}
	line.WriteString("}\n")
	_, _ = w.out.Write(line.Bytes())
}

func marshal(value any) []byte {
	var out bytes.Buffer
	encoder := json.NewEncoder(&out)
	encoder.SetEscapeHTML(false)
	if err := encoder.Encode(value); err != nil {
		return []byte("null")
	}
	return bytes.TrimRight(out.Bytes(), "\n")
}

// runtimeVersion is the Go release without its "go" prefix, like the other runners' versions.
func runtimeVersion() string {
	return strings.TrimPrefix(runtime.Version(), "go")
}

func (w *writer) hello() {
	w.emit(field{"event", "hello"}, field{"runner", runnerName},
		field{"protocol", protocolVersion}, field{"runtime", runtimeVersion()})
}

func (w *writer) jobStart(jobID string) {
	w.emit(field{"event", "job_start"}, field{"job_id", jobID})
}

func (w *writer) jobEnd(jobID string) { w.emit(field{"event", "job_end"}, field{"job_id", jobID}) }

func (w *writer) caseStart(jobID, caseID string) {
	w.emit(field{"event", "case_start"}, field{"job_id", jobID}, field{"case_id", caseID})
}

func (w *writer) caseResult(jobID, caseID string, o outcome) {
	w.emit(append([]field{{"event", "case_result"}, {"job_id", jobID}, {"case_id", caseID}},
		o.fields()...)...)
}

func (w *writer) loadError(jobID string, err *userError) {
	w.emit(field{"event", "load_error"}, field{"job_id", jobID}, field{"error", err})
}

// targetLoadError is bench mode's load_error: one target did not load, the others still run.
func (w *writer) targetLoadError(jobID, targetID string, err *userError) {
	w.emit(field{"event", "load_error"}, field{"job_id", jobID}, field{"target_id", targetID},
		field{"error", err})
}

func (w *writer) bye() { w.emit(field{"event", "bye"}) }

const (
	statusOK            = "ok"
	statusError         = "error"
	statusInvalidOutput = "invalid_output"
)

// outcome is what one call sequence produced: a case, or a bench check call.
type outcome struct {
	status string
	output any
	err    *userError
	reason string
	// opIndex is the failing operation of a class kind (with partialOutput), -1 otherwise.
	opIndex       int
	partialOutput []any
	durationNS    int64
	stdout        string
}

func returned(output any, durationNS int64) outcome {
	return outcome{status: statusOK, output: output, opIndex: -1, durationNS: durationNS}
}

func raised(err *userError, durationNS int64) outcome {
	return outcome{status: statusError, err: err, opIndex: -1, durationNS: durationNS}
}

func invalid(reason string, durationNS int64) outcome {
	return outcome{status: statusInvalidOutput, reason: reason, opIndex: -1, durationNS: durationNS}
}

// fields are the outcome's part of a case_result or bench_error; empty stdout is omitted.
func (o outcome) fields() []field {
	fields := []field{{"status", o.status}}
	switch o.status {
	case statusOK:
		fields = append(fields, field{"output", o.output})
	case statusError:
		fields = append(fields, field{"error", o.err})
		if o.opIndex >= 0 {
			fields = append(fields, field{"op_index", o.opIndex}, field{"partial_output", o.partialOutput})
		}
	case statusInvalidOutput:
		fields = append(fields, field{"reason", o.reason})
	}
	fields = append(fields, field{"duration_ns", o.durationNS})
	if o.stdout != "" {
		fields = append(fields, field{"stdout", o.stdout})
	}
	return fields
}

// benchPoint is one target at one input size of a bench job; every bench event names one.
type benchPoint struct {
	jobID    string
	targetID string
	size     int
}

func (p benchPoint) fields(event string) []field {
	return []field{{"event", event}, {"job_id", p.jobID}, {"target_id", p.targetID}, {"size", p.size}}
}

func (w *writer) benchStart(p benchPoint) { w.emit(p.fields("bench_start")...) }

func (w *writer) benchOutput(p benchPoint, output any) {
	w.emit(append(p.fields("bench_output"), field{"output", output})...)
}

func (w *writer) benchError(p benchPoint, o outcome) {
	w.emit(append(p.fields("bench_error"), o.fields()...)...)
}

// sample is `calls` back-to-back calls, each on a fresh input.
type sample struct {
	wallNS int64
	cpuNS  int64
	calls  int
}

func (s sample) perCallNS() int64 { return s.wallNS / int64(s.calls) }

func (w *writer) benchSample(p benchPoint, rep int, s sample) {
	w.emit(append(p.fields("bench_sample"), field{"rep", rep}, field{"wall_ns", s.wallNS},
		field{"cpu_ns", s.cpuNS}, field{"calls", s.calls})...)
}

func (w *writer) benchMemory(p benchPoint, metric string, bytes uint64) {
	w.emit(append(p.fields("bench_memory"), field{"metric", metric}, field{"bytes", bytes})...)
}

func (w *writer) benchBudgetExceeded(p benchPoint, wallNS int64) {
	w.emit(append(p.fields("bench_budget_exceeded"), field{"wall_ns", wallNS})...)
}
