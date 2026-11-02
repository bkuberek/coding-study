package runner

import (
	"strings"
	"testing"
	"testing/synctest"
)

const mailboxSignature = `{"class": {"name": "Mailbox", "constructor": {"params": []}, "methods": [
	{"name": "publish", "params": [{"name": "body", "type": "string"}], "returns": {"type": "int"}},
	{"name": "receive", "params": [{"name": "waitMs", "type": "int"}], "returns": {"type": "string"}},
	{"name": "hold", "params": [], "returns": {"type": "string"}},
	{"name": "leave", "params": [], "returns": {"type": "void"}},
	{"name": "fail", "params": [], "returns": {"type": "string"}}]}}`

const virtual = `"clock": "virtual", `

// mailboxJob is a project job of the fixture's Mailbox; clock is empty or `virtual`.
func mailboxJob(clock string, cases ...string) string {
	return `{"job_id": "j", "kind": "project", ` + clock + `"target": {"compiled": "user"},
		"names": {"class": "Mailbox", "constructor": "NewMailbox", "methods": {"publish": "Publish",
		"receive": "Receive", "hold": "Hold", "leave": "Leave", "fail": "Fail"}},
		"signature": ` + mailboxSignature + `, "cases": [` + strings.Join(cases, ",") + `]}`
}

func sequence(id, ops, args string) string {
	return `{"id": "` + id + `", "ops": ` + ops + `, "args": ` + args + `}`
}

// testClock is what the grading test of a virtual-clock test binary hands the runner.
func testClock(t *testing.T) *Clock {
	return &Clock{
		Bubble: func(body func()) { synctest.Test(t, func(*testing.T) { body() }) },
		Settle: synctest.Wait,
	}
}

func runOnClock(t *testing.T, jobs ...string) (int, []event) {
	t.Helper()
	return runRequest(t, &loader{registry: registry, clock: testClock(t)}, testRequest(jobs...))
}

// gradeOnClock runs one case that is expected to end the run normally.
func gradeOnClock(t *testing.T, ops, args string) event {
	t.Helper()
	code, events := runOnClock(t, mailboxJob(virtual, sequence("c", ops, args)))
	if code != exitCompleted {
		t.Fatalf("exit %d, events %v", code, events)
	}
	return onlyResult(t, events)
}

// stallOnClock runs a case that is expected to leave goroutines behind, then a second case that
// must not run in this process.
func stallOnClock(t *testing.T, ops, args string) (event, event) {
	t.Helper()
	next := sequence("next", `["Mailbox"]`, `[[]]`)
	code, events := runOnClock(t, mailboxJob(virtual, sequence("c", ops, args), next))
	if code != exitRestart || len(named(events, "bye")) != 0 || len(named(events, "case_start")) != 1 {
		t.Fatalf("exit %d, events %v", code, events)
	}
	return onlyResult(t, events), events[len(events)-1]
}

func TestHarnessOperationsRunOnTheVirtualClock(t *testing.T) {
	result := gradeOnClock(t,
		`["Mailbox", "@spawn", "@advance", "publish", "@join", "@now", "receive", "@now"]`,
		`[[], ["r1", "receive", 5000], [1000], ["a"], ["r1"], [], [2000], []]`)
	if result["status"] != "ok" || asJSON(result["output"]) != `[null,null,null,1,"a",1000,"",3000]` {
		t.Errorf("got %v", result)
	}
}

func TestEachCaseStartsItsClockAtZero(t *testing.T) {
	again := sequence("again", `["Mailbox", "@advance", "@now"]`, `[[], [1500], []]`)
	code, events := runOnClock(t, mailboxJob(virtual,
		sequence("first", `["Mailbox", "@advance", "@now"]`, `[[], [1500], []]`), again))
	results := named(events, "case_result")
	if code != exitCompleted || len(results) != 2 {
		t.Fatalf("exit %d, events %v", code, events)
	}
	for _, result := range results {
		if asJSON(result["output"]) != `[null,null,1500]` {
			t.Errorf("got %v", result)
		}
	}
}

func TestACaseTakesWallTimeNotVirtualTime(t *testing.T) {
	result := gradeOnClock(t, `["Mailbox", "@advance", "receive"]`, `[[], [60000], [30000]]`)
	if result["status"] != "ok" || result["duration_ns"].(float64) >= 5e9 {
		t.Errorf("got %v", result)
	}
}

func TestAProjectJobWithoutTheClockFieldStillRunsOnTheTestBinarysClock(t *testing.T) {
	code, events := runOnClock(t, mailboxJob("", sequence("c", `["Mailbox", "@advance", "@now"]`, `[[], [20], []]`)))
	result := onlyResult(t, events)
	if code != exitCompleted || asJSON(result["output"]) != `[null,null,20]` {
		t.Errorf("exit %d, got %v", code, result)
	}
}

func TestADeadlockIsStalledAtTheOperationAndTheVirtualTime(t *testing.T) {
	result, last := stallOnClock(t, `["Mailbox", "@advance", "@spawn", "@join"]`,
		`[[], [2000], ["r1", "hold"], ["r1"]]`)
	if result["status"] != "stalled" || result["op_index"] != float64(3) ||
		result["reason"] != "op 3 (@join r1): deadlock at 2000 ms" ||
		asJSON(result["partial_output"]) != `[null,null,null]` {
		t.Errorf("got %v", result)
	}
	if last["event"] != "restart_requested" || last["reason"] != "goroutines of c are still blocked" {
		t.Errorf("last event %v", last)
	}
}

func TestAMethodThatWaitsForeverIsStalledAtItsCall(t *testing.T) {
	result, _ := stallOnClock(t, `["Mailbox", "@advance", "hold"]`, `[[], [250], []]`)
	if result["status"] != "stalled" || result["op_index"] != float64(2) ||
		result["reason"] != "op 2 (hold): deadlock at 250 ms" {
		t.Errorf("got %v", result)
	}
}

func TestAGoroutineLeftWhenTheCaseEndsStallsIt(t *testing.T) {
	result, last := stallOnClock(t, `["Mailbox", "leave", "@advance", "@now"]`, `[[], [], [10], []]`)
	if result["status"] != "stalled" || result["op_index"] != float64(3) ||
		result["reason"] != "op 3 (@now): the case ended with goroutines still blocked at 10 ms" ||
		asJSON(result["partial_output"]) != `[null,null,null]` {
		t.Errorf("got %v", result)
	}
	if last["event"] != "restart_requested" {
		t.Errorf("last event %v", last)
	}
}

func TestAFailedCaseThatLeftAGoroutineKeepsItsErrorAndRestarts(t *testing.T) {
	result, last := stallOnClock(t, `["Mailbox", "leave", "fail"]`, `[[], [], []]`)
	failure := result["error"].(map[string]any)
	if result["status"] != "error" || result["op_index"] != float64(2) || failure["message"] != "mailbox closed" {
		t.Errorf("got %v", result)
	}
	if last["event"] != "restart_requested" {
		t.Errorf("last event %v", last)
	}
}

func TestAPanicInASpawnedCallIsTheErrorOfItsJoin(t *testing.T) {
	result := gradeOnClock(t, `["Mailbox", "@spawn", "@now", "@join"]`, `[[], ["f", "fail"], [], ["f"]]`)
	failure := result["error"].(map[string]any)
	if result["status"] != "error" || result["op_index"] != float64(3) ||
		failure["message"] != "mailbox closed" || asJSON(result["partial_output"]) != `[null,null,0]` ||
		!strings.Contains(failure["trace"].(string), "in Mailbox.Fail") {
		t.Errorf("got %v", result)
	}
}

func TestHarnessOperationsCheckTheirArguments(t *testing.T) {
	tests := []struct {
		name    string
		ops     string
		args    string
		opIndex float64
	}{
		{"join of an unknown task", `["Mailbox", "@join"]`, `[[], ["r1"]]`, 1},
		{"advance backwards", `["Mailbox", "@advance"]`, `[[], [-1]]`, 1},
		{"advance by a string", `["Mailbox", "@advance"]`, `[[], ["1000"]]`, 1},
		{"now with an argument", `["Mailbox", "@now"]`, `[[], [1]]`, 1},
		{"spawn without a method", `["Mailbox", "@spawn"]`, `[[], ["r1"]]`, 1},
		{"spawn of an unknown method", `["Mailbox", "@spawn"]`, `[[], ["r1", "wait"]]`, 1},
		{"spawn with the wrong arguments", `["Mailbox", "@spawn"]`, `[[], ["r1", "publish"]]`, 1},
		{"spawn of a running task", `["Mailbox", "@spawn", "@spawn"]`, `[[], ["r", "publish", "a"], ["r", "publish", "b"]]`, 2},
		{"unknown harness operation", `["Mailbox", "@wait"]`, `[[], []]`, 1},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := gradeOnClock(t, tt.ops, tt.args)
			failure, _ := result["error"].(map[string]any)
			if result["status"] != "error" || failure["type"] != "InvalidInput" || result["op_index"] != tt.opIndex {
				t.Errorf("got %v", result)
			}
		})
	}
}

func TestTheTestBinaryAnnouncesTheClock(t *testing.T) {
	_, events := runOnClock(t)
	if asJSON(events[0]["features"]) != `["stress","project","suite","project-stress","clock"]` {
		t.Errorf("hello: %v", events[0])
	}
}

func TestAVirtualClockJobNeedsTheTestBinary(t *testing.T) {
	events := runJobs(t, mailboxJob(virtual, sequence("c", `["Mailbox", "@now"]`, `[[], []]`)))
	failures := named(events, "load_error")
	if len(failures) != 1 || failures[0]["error"].(map[string]any)["type"] != "LoadError" {
		t.Errorf("got %v", events)
	}
}

func TestAProjectThatDidNotBuildAnswersAVirtualClockJob(t *testing.T) {
	broken := &loader{broken: map[string]*userError{"user": {Type: compileErrorType, Message: "store.go:3: undefined: x"}}}
	code, events := runRequest(t, broken, testRequest(mailboxJob(virtual, sequence("c", `["Mailbox"]`, `[[]]`))))
	failures := named(events, "load_error")
	if code != exitCompleted || !strings.Contains(asJSON(events[0]["features"]), `"clock"`) ||
		len(failures) != 1 || failures[0]["error"].(map[string]any)["type"] != compileErrorType {
		t.Errorf("exit %d, events %v", code, events)
	}
}

func TestTheVirtualClockBelongsToProjectJobsWithoutAsyncMethods(t *testing.T) {
	asyncMethod := strings.Replace(mailboxJob(virtual), `{"name": "hold", "params": []`,
		`{"name": "hold", "async": true, "params": []`, 1)
	designJob := strings.Replace(mailboxJob(virtual), `"kind": "project"`, `"kind": "design"`, 1)
	otherClock := mailboxJob(`"clock": "real", `)
	for _, job := range []string{asyncMethod, designJob, otherClock} {
		code, _ := runRequest(t, &loader{registry: registry, clock: testClock(t)}, testRequest(job))
		if code != exitBadRequest {
			t.Errorf("exit %d for %s", code, job)
		}
	}
}
