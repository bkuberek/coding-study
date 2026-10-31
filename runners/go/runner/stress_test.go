package runner

import (
	"strings"
	"testing"
)

const tallyJob = `{"job_id": "j", "kind": "concurrent", "model": "threads", "target": {"compiled": "user"},
	"names": {"class": "Tally", "constructor": "NewTally", "methods": {"increment": "Increment", "step": "Step"}},
	"signature": {"class": {"name": "Tally", "constructor": {"params": []}, "methods": [
		{"name": "increment", "params": [], "returns": {"type": "int"}},
		{"name": "step", "params": [{"name": "index", "type": "int"}], "returns": {"type": "int"}}]}},
	"cases": [CASES]}`

const gateJob = `{"job_id": "j", "kind": "concurrent", "model": "threads", "target": {"compiled": "user"},
	"names": {"class": "Gate", "constructor": "NewGate", "methods": {"enter": "Enter"}},
	"signature": {"class": {"name": "Gate", "constructor": {"params": []}, "methods": [
		{"name": "enter", "params": [], "returns": {"type": "void"}}]}},
	"cases": [CASES]}`

// stress is one stress run case: the setup and workers as JSON, an optional final script.
func stress(id string, deadlineMS string, setup string, workers []string, final string) string {
	body := `{"id": "` + id + `", "stress": {"seed": 7, "deadline_ms": ` + deadlineMS + `,
		"perturb": {"yield_probability": 0.5, "max_yields": 3, "python_granularity": "line"},
		"setup": ` + setup + `, "workers": [` + strings.Join(workers, ",") + `]`
	if final != "" {
		body += `, "final": ` + final
	}
	return body + `}}`
}

// repeated is a script that repeats one op with the same arguments.
func repeated(op, args string, times int) string {
	ops := strings.TrimSuffix(strings.Repeat(`"`+op+`",`, times), ",")
	argLists := strings.TrimSuffix(strings.Repeat(args+",", times), ",")
	return `{"ops": [` + ops + `], "args": [` + argLists + `]}`
}

// steps is a script of `step` ops with the indices from 0 to count-1.
func steps(count int) string {
	var args []string
	for index := range count {
		args = append(args, "["+asJSON(index)+"]")
	}
	return `{"ops": [` + strings.TrimSuffix(strings.Repeat(`"step",`, count), ",") + `], "args": [` +
		strings.Join(args, ",") + `]}`
}

func withCases(job string, cases ...string) string {
	return strings.Replace(job, "CASES", strings.Join(cases, ","), 1)
}

const tallySetup = `{"ops": ["Tally"], "args": [[]]}`

func TestHelloAnnouncesTheStressProjectAndSuiteFeatures(t *testing.T) {
	events := runJobs(t)
	if asJSON(events[0]["features"]) != `["stress","project","suite"]` {
		t.Errorf("hello: %v", events[0])
	}
}

func TestAStressRunReportsEveryOutput(t *testing.T) {
	increments := repeated("increment", "[]", 50)
	job := withCases(tallyJob,
		`{"id": "ex1", "ops": ["Tally", "increment"], "args": [[], []]}`,
		stress("s1:thread:0", "5000", tallySetup, []string{increments, increments, increments, increments},
			`{"ops": ["increment"], "args": [[]]}`))
	results := named(runJobs(t, job), "case_result")
	if len(results) != 2 || asJSON(results[0]["output"]) != "[null,1]" {
		t.Fatalf("got %v", results)
	}
	result := results[1]
	output, ok := result["output"].(map[string]any)
	if result["status"] != "ok" || !ok || asJSON(result["sections"]) != "{}" {
		t.Fatalf("got %v", result)
	}
	seen := map[float64]bool{}
	for _, worker := range output["workers"].([]any) {
		for _, value := range worker.([]any) {
			seen[value.(float64)] = true
		}
	}
	if asJSON(output["setup"]) != "[null]" || len(seen) != 200 || asJSON(output["final"]) != "[201]" {
		t.Errorf("output %s", asJSON(output))
	}
	if result["duration_ns"].(float64) <= 0 {
		t.Errorf("duration %v", result["duration_ns"])
	}
}

func TestAStressRunWithoutFinalReportsAnEmptyFinal(t *testing.T) {
	increments := repeated("increment", "[]", 1)
	job := withCases(tallyJob, stress("s1", "5000", tallySetup, []string{increments, increments}, ""))
	output := onlyResult(t, runJobs(t, job))["output"].(map[string]any)
	if asJSON(output["final"]) != "[]" {
		t.Errorf("output %s", asJSON(output))
	}
}

func TestProbeSectionsCountOverlappingEntries(t *testing.T) {
	setup := `{"ops": ["Tally", "@enter", "@enter", "@pause", "@exit", "@exit"],
		"args": [[], ["data", "exclusive"], ["data", "shared"], [2], ["data"], ["data"]]}`
	probe := `{"ops": ["@enter", "@exit"], "args": [["data", "shared"], ["data"]]}`
	job := withCases(tallyJob, stress("s1", "5000", setup, []string{probe, probe}, ""))
	result := onlyResult(t, runJobs(t, job))
	section := result["sections"].(map[string]any)["data"].(map[string]any)
	if result["status"] != "ok" || section["entries"] != float64(4) || section["violations"] != float64(1) ||
		section["max_occupancy"].(float64) < 2 {
		t.Errorf("got %v", result)
	}
}

func TestAnExitWithoutEnterIsAHarnessError(t *testing.T) {
	exit := `{"ops": ["@exit"], "args": [["data"]]}`
	job := withCases(tallyJob, stress("s1", "5000", tallySetup, []string{exit, repeated("increment", "[]", 1)}, ""))
	result := onlyResult(t, runJobs(t, job))
	failure := result["error"].(map[string]any)
	if result["status"] != "error" || result["phase"] != "worker" || result["worker"] != float64(0) ||
		result["op_index"] != float64(0) || failure["type"] != "HarnessError" ||
		failure["message"] != `@exit "data" without a matching @enter` {
		t.Errorf("got %v", result)
	}
}

func TestAWorkerPanicNamesItsPhaseWorkerAndOp(t *testing.T) {
	job := withCases(tallyJob, stress("s1", "5000", tallySetup, []string{steps(200), steps(200)}, ""))
	result := onlyResult(t, runJobs(t, job))
	failure := result["error"].(map[string]any)
	if result["status"] != "error" || result["phase"] != "worker" || result["op_index"] != float64(100) ||
		failure["message"] != "failed at 100" || !strings.HasSuffix(failure["trace"].(string), " in Tally.Step") {
		t.Fatalf("got %v", result)
	}
	failing := result["worker"].(float64)
	var listed bool
	for _, item := range result["progress"].([]any) {
		progress := item.(map[string]any)
		if progress["worker"] == failing {
			listed = progress["in_op"] == true && progress["completed"] == float64(100)
		}
	}
	if !listed {
		t.Errorf("progress %v", result["progress"])
	}
}

func TestSetupAndDecodingFailuresNameTheirPhase(t *testing.T) {
	failingSetup := `{"ops": ["Tally", "step"], "args": [[], [100]]}`
	badArgument := `{"ops": ["step"], "args": [["x"]]}`
	job := withCases(tallyJob,
		stress("setup", "5000", failingSetup, []string{steps(1), steps(1)}, ""),
		stress("decode", "5000", tallySetup, []string{steps(1), badArgument}, ""))
	results := named(runJobs(t, job), "case_result")
	if results[0]["phase"] != "setup" || results[0]["op_index"] != float64(1) || results[0]["worker"] != nil {
		t.Errorf("setup: %v", results[0])
	}
	failure := results[1]["error"].(map[string]any)
	if results[1]["phase"] != "worker" || results[1]["worker"] != float64(1) || failure["type"] != "InvalidInput" {
		t.Errorf("decode: %v", results[1])
	}
}

func TestAStalledRunAsksForARestart(t *testing.T) {
	enter := repeated("enter", "[]", 1)
	setup := `{"ops": ["Gate"], "args": [[]]}`
	job := withCases(gateJob, stress("s1", "100", setup, []string{enter, enter}, ""),
		stress("s2", "100", setup, []string{enter, enter}, ""))
	code, events := runRequest(t, &loader{registry: registry}, testRequest(job))
	if code != exitRestart || len(named(events, "bye")) != 0 || len(named(events, "case_start")) != 1 {
		t.Fatalf("exit %d, events %v", code, events)
	}
	result := onlyResult(t, events)
	if result["status"] != "stalled" ||
		asJSON(result["progress"]) != `[{"completed":0,"in_op":true,"worker":0},{"completed":0,"in_op":true,"worker":1}]` {
		t.Errorf("got %v", result)
	}
	last := events[len(events)-1]
	if last["event"] != "restart_requested" || last["reason"] != "2 worker goroutines still running after s1" {
		t.Errorf("last event %v", last)
	}
}
