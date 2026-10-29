package runner

import (
	"bufio"
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"cstudy/runner/internal/fixture"
)

type event map[string]any

var registry = Registry{
	"user": {
		"twoSum": fixture.TwoSum, "indexAt": fixture.IndexAt, "shout": fixture.Shout,
		"loud": fixture.Loud, "overflow": fixture.Overflow, "sortValues": fixture.SortValues,
		"pickNode": fixture.PickNode, "sameList": fixture.SameList, "NewCounter": fixture.NewCounter,
		"wrong": fixture.Wrong, "NewTally": fixture.NewTally, "NewGate": fixture.NewGate,
		"third": fixture.Third, "price": fixture.Price,
	},
	"ref/new-node": {"pickNode": fixture.NewNode},
}

const twoSumSignature = `{"function": {"name": "twoSum", "params": [{"name": "nums", "type": "int[]"},
	{"name": "target", "type": "int"}], "returns": {"type": "int[]"}}}`

func function(name, signature, cases string) string {
	return `{"job_id": "j", "kind": "function", "target": {"compiled": "user"},
		"names": {"function": "` + name + `"}, "signature": ` + signature + `, "cases": ` + cases + `}`
}

func oneParam(name, typeText, returnType string) string {
	return `{"function": {"name": "` + name + `", "params": [{"name": "value", "type": "` + typeText +
		`"}], "returns": {"type": "` + returnType + `"}}}`
}

// runRequest runs a request through the runner and returns the exit code and the events.
func runRequest(t *testing.T, l *loader, body string) (int, []event) {
	t.Helper()
	directory := t.TempDir()
	requestPath := filepath.Join(directory, "request.json")
	outPath := filepath.Join(directory, "events.jsonl")
	if err := os.WriteFile(requestPath, []byte(body), 0o600); err != nil {
		t.Fatal(err)
	}
	var stderr bytes.Buffer
	code := run(l, []string{"--request", requestPath, "--out", outPath}, &stderr)
	data, err := os.ReadFile(outPath)
	if err != nil {
		t.Fatal(err)
	}
	var events []event
	scanner := bufio.NewScanner(bytes.NewReader(data))
	scanner.Buffer(nil, 1<<20)
	for scanner.Scan() {
		var e event
		if err := json.Unmarshal(scanner.Bytes(), &e); err != nil {
			t.Fatalf("not JSON: %s", scanner.Text())
		}
		events = append(events, e)
	}
	return code, events
}

func testRequest(jobs ...string) string {
	return `{"protocol": 1, "mode": "test", "jobs": [` + strings.Join(jobs, ",") + `]}`
}

func runJobs(t *testing.T, jobs ...string) []event {
	t.Helper()
	code, events := runRequest(t, &loader{registry: registry}, testRequest(jobs...))
	if code != exitCompleted {
		t.Fatalf("exit %d", code)
	}
	return events
}

func named(events []event, name string) []event {
	var found []event
	for _, e := range events {
		if e["event"] == name {
			found = append(found, e)
		}
	}
	return found
}

func onlyResult(t *testing.T, events []event) event {
	t.Helper()
	results := named(events, "case_result")
	if len(results) != 1 {
		t.Fatalf("got %d case results: %v", len(results), events)
	}
	return results[0]
}

func asJSON(value any) string { return string(marshal(value)) }

func TestEventsFollowTheProtocolOrder(t *testing.T) {
	events := runJobs(t, function("twoSum", twoSumSignature,
		`[{"id": "ex1", "input": {"nums": [4, 9, 2, 7], "target": 11}}]`))
	var order []string
	for _, e := range events {
		order = append(order, e["event"].(string))
	}
	want := "hello job_start case_start case_result job_end bye"
	if got := strings.Join(order, " "); got != want {
		t.Errorf("got %s, want %s", got, want)
	}
	if events[0]["runner"] != "go" || events[0]["protocol"] != float64(1) {
		t.Errorf("hello: %v", events[0])
	}
}

func TestFunctionCases(t *testing.T) {
	tests := []struct {
		name   string
		job    string
		status string
		output string
	}{
		{"returns", function("twoSum", twoSumSignature, `[{"id": "c", "input": {"nums": [4, 9, 2, 7], "target": 11}}]`), "ok", "[1,2]"},
		{"nil slice", function("twoSum", twoSumSignature, `[{"id": "c", "input": {"nums": [1], "target": 5}}]`), "ok", "[]"},
		{"output_from", function("sortValues", `{"function": {"name": "sortValues", "params": [{"name": "values", "type": "int[]"}], "returns": {"type": "void", "output_from": "values"}}}`, `[{"id": "c", "input": {"values": [3, 1, 2]}}]`), "ok", "[1,2,3]"},
		{"ref_of as index", function("pickNode", pickNodeSignature, `[{"id": "c", "input": {"head": [5, 6, 7], "node": 6}}]`), "ok", "1"},
		{"int out of range", function("overflow", oneParam("overflow", "int", "int"), `[{"id": "c", "input": {"value": 1}}]`), "invalid_output", ""},
		{"no_alias_with", function("sameList", `{"function": {"name": "sameList", "params": [{"name": "head", "type": "ListNode"}], "returns": {"type": "ListNode", "no_alias_with": "head"}}}`, `[{"id": "c", "input": {"head": [1, 2]}}]`), "invalid_output", ""},
		{"missing input", function("twoSum", twoSumSignature, `[{"id": "c", "input": {"nums": [1]}}]`), "error", ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := onlyResult(t, runJobs(t, tt.job))
			if result["status"] != tt.status {
				t.Fatalf("got %v", result)
			}
			if tt.output != "" && asJSON(result["output"]) != tt.output {
				t.Errorf("output %s, want %s", asJSON(result["output"]), tt.output)
			}
			if _, ok := result["duration_ns"]; !ok {
				t.Error("no duration_ns")
			}
		})
	}
}

const pickNodeSignature = `{"function": {"name": "pickNode", "params": [{"name": "head", "type": "ListNode"},
	{"name": "node", "type": "ListNode", "ref_of": "head"}], "returns": {"type": "ListNode", "as": "index", "of": "head"}}}`

func TestANodeOutsideTheParameterIsAnInvalidIndex(t *testing.T) {
	job := strings.Replace(function("pickNode", pickNodeSignature, `[{"id": "c", "input": {"head": [5, 6], "node": 6}}]`),
		`"compiled": "user"`, `"compiled": "ref/new-node"`, 1)
	result := onlyResult(t, runJobs(t, job))
	if result["status"] != "invalid_output" || result["reason"] != `the returned node is not a node of "head"` {
		t.Errorf("got %v", result)
	}
}

func TestAPanicIsAnErrorWithUserFrames(t *testing.T) {
	signature := `{"function": {"name": "indexAt", "params": [{"name": "nums", "type": "int[]"}, {"name": "index", "type": "int"}], "returns": {"type": "int"}}}`
	result := onlyResult(t, runJobs(t, function("indexAt", signature, `[{"id": "c", "input": {"nums": [1, 2, 3], "index": 5}}]`)))
	failure := result["error"].(map[string]any)
	if failure["type"] != "runtime.boundsError" || failure["message"] != "runtime error: index out of range [5] with length 3" {
		t.Errorf("got %v", failure)
	}
	trace := failure["trace"].(string)
	lines := strings.Split(trace, "\n")
	if len(lines) != 2 || !strings.HasSuffix(lines[0], " in IndexAt") || !strings.HasSuffix(lines[1], " in pick") {
		t.Errorf("trace %q", trace)
	}
}

func TestStandardOutputAndErrorAreCaptured(t *testing.T) {
	result := onlyResult(t, runJobs(t, function("shout", oneParam("shout", "string", "string"), `[{"id": "c", "input": {"value": "hi"}}]`)))
	if result["stdout"] != "hi\nhi\n" {
		t.Errorf("stdout %q", result["stdout"])
	}
}

func TestCapturedOutputIsTruncatedAt4KiB(t *testing.T) {
	result := onlyResult(t, runJobs(t, function("loud", oneParam("loud", "int", "int"), `[{"id": "c", "input": {"value": 70000}}]`)))
	want := strings.Repeat("x", maxOutputBytes) + truncationNotice
	if result["stdout"] != want || result["status"] != "ok" {
		t.Errorf("status %v, stdout of %d bytes", result["status"], len(result["stdout"].(string)))
	}
}

func TestLoadErrors(t *testing.T) {
	tests := []struct {
		name    string
		job     string
		l       *loader
		errType string
		message string
	}{
		{"missing symbol", function("echoNumber", oneParam("echoNumber", "int", "int"), `[]`),
			&loader{registry: registry, unavailable: Unavailable{"user": {"echoNumber": "undefined: echoNumber"}}},
			"SymbolNotFound", `the package defines no function "echoNumber": undefined: echoNumber`},
		{"wrong parameter type", function("wrong", strings.Replace(twoSumSignature, "twoSum", "wrong", 1), `[]`),
			&loader{registry: registry}, "SignatureMismatch", `"wrong" takes []int64 for "nums"; int[] is []int in Go`},
		{"float for a decimal", function("price", oneParam("price", "decimal", "decimal"), `[]`),
			&loader{registry: registry}, "SignatureMismatch", `"price" takes float64 for "value"; decimal is decimal.Decimal in Go`},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, events := runRequest(t, tt.l, testRequest(tt.job))
			loadErrors := named(events, "load_error")
			if len(loadErrors) != 1 || len(named(events, "case_start")) != 0 {
				t.Fatalf("got %v", events)
			}
			failure := loadErrors[0]["error"].(map[string]any)
			if failure["type"] != tt.errType || failure["message"] != tt.message {
				t.Errorf("got %v", failure)
			}
		})
	}
}

const counterJob = `{"job_id": "j", "kind": "design", "target": {"compiled": "user"},
	"names": {"class": "Counter", "constructor": "NewCounter", "methods": {"increment": "Increment", "fail": "Fail"}},
	"signature": {"class": {"name": "Counter", "constructor": {"params": []}, "methods": [
		{"name": "increment", "params": [], "returns": {"type": "int"}},
		{"name": "fail", "params": [], "returns": {"type": "void"}}]}},
	"cases": [
		{"id": "counts", "ops": ["Counter", "increment", "increment"], "args": [[], [], []]},
		{"id": "fails", "ops": ["Counter", "increment", "increment", "fail"], "args": [[], [], [], []]},
		{"id": "unknown", "ops": ["Counter", "decrement"], "args": [[], []]}]}`

func TestClassCases(t *testing.T) {
	results := named(runJobs(t, counterJob), "case_result")
	if asJSON(results[0]["output"]) != "[null,1,2]" {
		t.Errorf("counts: %v", results[0])
	}
	failure := results[1]["error"].(map[string]any)
	if results[1]["op_index"] != float64(3) || asJSON(results[1]["partial_output"]) != "[null,1,2]" ||
		failure["message"] != "counter failure" || !strings.HasSuffix(failure["trace"].(string), " in Counter.Fail") {
		t.Errorf("fails: %v", results[1])
	}
	if results[2]["status"] != "error" || results[2]["op_index"] != float64(1) {
		t.Errorf("unknown: %v", results[2])
	}
}

func TestBadRequestsExitWith2(t *testing.T) {
	tests := []struct{ name, body string }{
		{"not JSON", "{"},
		{"unknown protocol", `{"protocol": 2, "mode": "test", "jobs": []}`},
		{"async model", testRequest(`{"job_id": "j", "kind": "concurrent", "model": "async", "signature": {"class": {}}}`)},
		{"concurrent bench", `{"protocol": 1, "mode": "bench", "jobs": [{"job_id": "j", "kind": "concurrent",
			"model": "threads", "signature": {"class": {}}, "targets": [{"target_id": "user", "target": {"compiled": "user"}}]}]}`},
		{"stress case outside a concurrent job", testRequest(`{"job_id": "j", "kind": "design", "signature": {"class": {}},
			"cases": [{"id": "s1", "stress": {"setup": {"ops": [], "args": []}, "workers": []}}]}`)},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			code, events := runRequest(t, &loader{registry: registry}, tt.body)
			if code != exitBadRequest || len(named(events, "bye")) != 0 {
				t.Errorf("exit %d, events %v", code, events)
			}
		})
	}
}

func TestBenchReportsSamplesOutputsAndMemory(t *testing.T) {
	body := `{"protocol": 1, "mode": "bench", "jobs": [{"job_id": "j", "kind": "function",
		"signature": ` + twoSumSignature + `,
		"targets": [
			{"target_id": "user", "target": {"compiled": "user"}, "names": {"function": "twoSum"}, "output": true},
			{"target_id": "missing", "target": {"compiled": "user"}, "names": {"function": "absent"}}],
		"inputs": [{"size": 4, "input": {"nums": [4, 9, 2, 7], "target": 11}, "max_batch": 100}],
		"settings": {"reps": 3, "warmup": {"min": 1, "max": 3, "cv": 0.05}, "budget_ms": 2000, "memory": true, "min_sample_ns": 1000}}]}`
	code, events := runRequest(t, &loader{registry: registry}, body)
	if code != exitCompleted {
		t.Fatalf("exit %d", code)
	}
	if loadErrors := named(events, "load_error"); len(loadErrors) != 1 || loadErrors[0]["target_id"] != "missing" {
		t.Errorf("load errors %v", loadErrors)
	}
	if outputs := named(events, "bench_output"); len(outputs) != 1 || asJSON(outputs[0]["output"]) != "[1,2]" {
		t.Errorf("outputs %v", outputs)
	}
	samples := named(events, "bench_sample")
	if len(samples) != 3 || samples[2]["rep"] != float64(3) || samples[0]["calls"].(float64) < 1 {
		t.Errorf("samples %v", samples)
	}
	memory := named(events, "bench_memory")
	if len(memory) != 1 || memory[0]["metric"] != memoryMetric {
		t.Errorf("memory %v", memory)
	}
}

func TestBenchStopsATargetThatPanics(t *testing.T) {
	signature := `{"function": {"name": "indexAt", "params": [{"name": "nums", "type": "int[]"}, {"name": "index", "type": "int"}], "returns": {"type": "int"}}}`
	body := `{"protocol": 1, "mode": "bench", "jobs": [{"job_id": "j", "kind": "function", "signature": ` + signature + `,
		"targets": [{"target_id": "user", "target": {"compiled": "user"}, "names": {"function": "indexAt"}}],
		"inputs": [{"size": 1, "input": {"nums": [1], "index": 3}, "max_batch": 10}],
		"settings": {"reps": 3, "warmup": {"min": 1, "max": 3, "cv": 0.05}, "budget_ms": 2000, "memory": false, "min_sample_ns": 1000}}]}`
	_, events := runRequest(t, &loader{registry: registry}, body)
	errors := named(events, "bench_error")
	if len(errors) != 1 || errors[0]["status"] != "error" || len(named(events, "bench_sample")) != 0 {
		t.Errorf("got %v", events)
	}
}
