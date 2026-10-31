package runner

import (
	"bytes"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

// fileNames gives every test the id <package>_test.go::<name>.
type fileNames struct{}

func (fileNames) id(importPath, name string) string { return importPath + "_test.go::" + name }

type recorded struct {
	translator *translator
	out        *bytes.Buffer
}

func newRecorded(skip ...string) *recorded {
	var out bytes.Buffer
	return &recorded{translator: newTranslator("j", "/ws/p", &writer{out: &out}, fileNames{}, skip), out: &out}
}

func (r *recorded) feed(events ...testEvent) *recorded {
	for _, e := range events {
		r.translator.handle(e)
	}
	return r
}

func (r *recorded) events(t *testing.T) []event {
	t.Helper()
	var found []event
	for _, line := range strings.Split(strings.TrimSpace(r.out.String()), "\n") {
		if line == "" {
			continue
		}
		var e event
		if err := json.Unmarshal([]byte(line), &e); err != nil {
			t.Fatalf("not JSON: %s", line)
		}
		found = append(found, e)
	}
	return found
}

// summary lists the events as `start id` and `<status> id`.
func (r *recorded) summary(t *testing.T) []string {
	t.Helper()
	var lines []string
	for _, e := range r.events(t) {
		switch e["event"] {
		case "case_start":
			lines = append(lines, "start "+e["case_id"].(string))
		case "case_result":
			lines = append(lines, e["status"].(string)+" "+e["case_id"].(string))
		default:
			lines = append(lines, e["event"].(string))
		}
	}
	return lines
}

func (r *recorded) result(t *testing.T, id string) event {
	t.Helper()
	for _, e := range r.events(t) {
		if e["event"] == "case_result" && e["case_id"] == id {
			return e
		}
	}
	t.Fatalf("no result for %s in %s", id, r.out.String())
	return nil
}

func started(name string) testEvent { return testEvent{Action: "run", Package: "p", Test: name} }

func out(name, text string) testEvent {
	return testEvent{Action: "output", Package: "p", Test: name, Output: text}
}

func end(action, name string) testEvent {
	return testEvent{Action: action, Package: "p", Test: name, Elapsed: 0.25}
}

func closing(action string) []testEvent {
	upper := strings.ToUpper(action)
	return []testEvent{
		{Action: "output", Package: "p", Output: upper + "\n"},
		{Action: action, Package: "p"},
	}
}

func joined(summary []string) string { return strings.Join(summary, " | ") }

func TestAPassingTestIsOkWithItsOutput(t *testing.T) {
	r := newRecorded().feed(started("TestA"), out("TestA", "=== RUN   TestA\n"), out("TestA", "hello\n"),
		out("TestA", "--- PASS: TestA (0.25s)\n"), end("pass", "TestA"))
	result := r.result(t, "p_test.go::TestA")
	if result["status"] != "ok" || result["stdout"] != "hello\n" || result["duration_ns"] != 250e6 {
		t.Errorf("result %v", result)
	}
}

func TestAFailingTestIsFailedWithItsMessage(t *testing.T) {
	r := newRecorded().feed(started("TestA"), out("TestA", "    a_test.go:9: got 1, want 2\n"),
		out("TestA", "        second line\n"), out("TestA", "--- FAIL: TestA (0.00s)\n"), end("fail", "TestA"))
	result := r.result(t, "p_test.go::TestA")
	if result["status"] != "failed" || result["message"] != "a_test.go:9: got 1, want 2\n    second line" {
		t.Errorf("result %v", result)
	}
}

func TestASkippedTestGivesItsReason(t *testing.T) {
	r := newRecorded().feed(started("TestA"), out("TestA", "    a_test.go:3: not today\n"), end("skip", "TestA"))
	if result := r.result(t, "p_test.go::TestA"); result["message"] != "a_test.go:3: not today" {
		t.Errorf("result %v", result)
	}
}

func TestEverySubtestIsATestOfItsOwnBeforeItsParent(t *testing.T) {
	r := newRecorded().feed(started("TestA"), started("TestA/ok"), end("pass", "TestA/ok"), started("TestA/bad"),
		out("TestA/bad", "    a_test.go:5: bad\n"), end("fail", "TestA/bad"), end("fail", "TestA"))
	want := "start p_test.go::TestA/ok | ok p_test.go::TestA/ok | start p_test.go::TestA/bad | " +
		"failed p_test.go::TestA/bad | start p_test.go::TestA | failed p_test.go::TestA"
	if got := joined(r.summary(t)); got != want {
		t.Errorf("events %s", got)
	}
}

func TestAPackageThatDoesNotBuildIsOneCompileError(t *testing.T) {
	r := newRecorded().feed(
		testEvent{Action: "build-output", ImportPath: "p [p.test]", Output: "# p [p.test]\n"},
		testEvent{Action: "build-output", ImportPath: "p [p.test]", Output: "./x_test.go:4:2: undefined: y\n"},
		testEvent{Action: "build-fail", ImportPath: "p [p.test]"},
		testEvent{Action: "fail", Package: "p", FailedBuild: "p [p.test]"})
	failure := r.result(t, "p")["error"].(map[string]any)
	if failure["type"] != "CompileError" || failure["message"] != "x_test.go:4:2: undefined: y" ||
		failure["trace"] != "x_test.go:4" {
		t.Errorf("error %v", failure)
	}
}

func TestAPanicCrashesItsTestAfterTheOtherResults(t *testing.T) {
	r := newRecorded().feed(started("TestA"), end("pass", "TestA"), started("TestB"),
		out("TestB", "--- FAIL: TestB (0.00s)\n"), out("TestB", "panic: boom [recovered]\n"),
		out("TestB", "goroutine 7 [running]:\n"), end("fail", "TestB"),
		testEvent{Action: "fail", Package: "p"})
	var stderr bytes.Buffer
	if r.translator.conclude(&stderr) {
		t.Fatal("concluded without a crash")
	}
	want := "start p_test.go::TestA | ok p_test.go::TestA | start p_test.go::TestB"
	if got := joined(r.summary(t)); got != want {
		t.Errorf("events %s", got)
	}
	if !strings.HasSuffix(stderr.String(), "panic: boom [recovered]\n") {
		t.Errorf("stderr %q", stderr.String())
	}
}

func TestATestThatEndsTheBinaryCrashes(t *testing.T) {
	r := newRecorded().feed(started("TestA"), end("pass", "TestA"), started("TestB"),
		out("TestB", "=== RUN   TestB\n"), testEvent{Action: "fail", Package: "p"})
	var stderr bytes.Buffer
	r.translator.conclude(&stderr)
	want := "start p_test.go::TestA | ok p_test.go::TestA | start p_test.go::TestB"
	if got := joined(r.summary(t)); got != want {
		t.Errorf("events %s", got)
	}
	if stderr.String() != "the test binary of p ended during TestB\n" {
		t.Errorf("stderr %q", stderr.String())
	}
}

func TestAPanicThatTheBinarySurvivesIsAFailure(t *testing.T) {
	r := newRecorded().feed(started("TestA"), out("TestA", "panic: printed\n"), end("fail", "TestA"))
	r.feed(closing("fail")...)
	if result := r.result(t, "p_test.go::TestA"); result["status"] != "failed" {
		t.Errorf("result %v", result)
	}
}

func TestABinaryThatEndsOutsideAnyTestIsAnErrorOnItsPackage(t *testing.T) {
	r := newRecorded().feed(testEvent{Action: "output", Package: "p", Output: "exit status 3\n"},
		testEvent{Action: "fail", Package: "p"})
	failure := r.result(t, "p")["error"].(map[string]any)
	if failure["type"] != "TestBinaryExited" || failure["message"] != "exit status 3" {
		t.Errorf("error %v", failure)
	}
}

func TestAQuietRunNamesTheEarliestRunningTestInProgress(t *testing.T) {
	r := newRecorded().feed(started("TestA"), started("TestB"))
	r.translator.quiet()
	if got := joined(r.summary(t)); got != "start p_test.go::TestA" {
		t.Errorf("events %s", got)
	}
}

func TestResultsWaitForTheTestInProgress(t *testing.T) {
	r := newRecorded().feed(started("TestA"), started("TestB"))
	r.translator.quiet()
	r.feed(end("pass", "TestB"), end("pass", "TestA"))
	want := "start p_test.go::TestA | ok p_test.go::TestA | start p_test.go::TestB | ok p_test.go::TestB"
	if got := joined(r.summary(t)); got != want {
		t.Errorf("events %s", got)
	}
}

func TestAPausedTestIsNeverNamedInProgress(t *testing.T) {
	r := newRecorded().feed(started("TestA"), testEvent{Action: "pause", Package: "p", Test: "TestA"})
	r.translator.quiet()
	if got := r.summary(t); len(got) != 0 {
		t.Errorf("events %v", got)
	}
}

func TestAParentWithARunningSubtestIsNotNamedInProgress(t *testing.T) {
	r := newRecorded().feed(started("TestA"), started("TestA/sub"))
	r.translator.quiet()
	if got := joined(r.summary(t)); got != "start p_test.go::TestA/sub" {
		t.Errorf("events %s", got)
	}
}

func TestAHangIsLeftWithItsTestInProgress(t *testing.T) {
	r := newRecorded().feed(started("TestA"))
	lines := make(chan []byte)
	done := make(chan struct{})
	go func() {
		r.translator.follow(lines, 10*time.Millisecond)
		close(done)
	}()
	time.Sleep(50 * time.Millisecond)
	close(lines)
	<-done
	if got := joined(r.summary(t)); got != "start p_test.go::TestA" {
		t.Errorf("events %s", got)
	}
}

func TestATestReportedBeforeARestartIsNotReportedAgain(t *testing.T) {
	r := newRecorded("p_test.go::TestA").feed(started("TestA"), end("pass", "TestA"))
	if got := r.summary(t); len(got) != 0 {
		t.Errorf("events %v", got)
	}
}

// A real project, run through `go test`.

const suiteModule = "module suite\n\ngo 1.24\n"

func writeProject(t *testing.T, files map[string]string) string {
	t.Helper()
	root := t.TempDir()
	files["go.mod"] = suiteModule
	for name, text := range files {
		path := filepath.Join(root, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte(text), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	return root
}

func suiteRequestBody(root string, fields string) string {
	return testRequest(`{"job_id": "s", "kind": "suite", "framework": "go-test", "root": ` +
		asJSON(root) + fields + `}`)
}

func runSuite(t *testing.T, root, fields string) (int, []event, string) {
	t.Helper()
	if testing.Short() {
		t.Skip("runs go test")
	}
	if _, err := exec.LookPath("go"); err != nil {
		t.Skip("go is not installed")
	}
	t.Setenv("GOWORK", "off")
	t.Setenv("GOFLAGS", "-mod=mod")
	directory := t.TempDir()
	requestPath := filepath.Join(directory, "request.json")
	outPath := filepath.Join(directory, "events.jsonl")
	if err := os.WriteFile(requestPath, []byte(suiteRequestBody(root, fields)), 0o600); err != nil {
		t.Fatal(err)
	}
	var stderr bytes.Buffer
	code := run(&loader{}, []string{"--request", requestPath, "--out", outPath}, &stderr)
	data, _ := os.ReadFile(outPath)
	var events []event
	for _, line := range strings.Split(strings.TrimSpace(string(data)), "\n") {
		var e event
		if err := json.Unmarshal([]byte(line), &e); err != nil {
			t.Fatalf("not JSON: %s", line)
		}
		events = append(events, e)
	}
	return code, events, stderr.String()
}

func statuses(events []event) map[string]string {
	found := map[string]string{}
	for _, e := range events {
		if e["event"] == "case_result" {
			found[e["case_id"].(string)] = e["status"].(string)
		}
	}
	return found
}

const projectSource = "package suite\n\nfunc Double(n int) int { return 2 * n }\n"

const projectTestFile = `package suite

import "testing"

func TestPasses(t *testing.T) {
	if Double(2) != 4 {
		t.Fatal("no")
	}
}

func TestFails(t *testing.T) { t.Errorf("Double(1) = %d, want 3", Double(1)) }

func TestSkips(t *testing.T) { t.Skip("not today") }

func TestTable(t *testing.T) {
	t.Run("ok", func(t *testing.T) {})
	t.Run("bad case", func(t *testing.T) { t.Error("bad") })
}
`

func TestASuiteReportsEveryTestUnderItsFile(t *testing.T) {
	root := writeProject(t, map[string]string{"suite.go": projectSource, "suite_test.go": projectTestFile})
	code, events, _ := runSuite(t, root, "")
	want := map[string]string{
		"suite_test.go::TestPasses": "ok", "suite_test.go::TestFails": "failed",
		"suite_test.go::TestSkips": "skipped", "suite_test.go::TestTable/ok": "ok",
		"suite_test.go::TestTable/bad_case": "failed", "suite_test.go::TestTable": "failed",
	}
	if code != exitCompleted || asJSON(statuses(events)) != asJSON(want) {
		t.Errorf("exit %d, statuses %v", code, statuses(events))
	}
}

func TestAPackageWhoseTestsDoNotCompileIsReportedAndTheOthersRun(t *testing.T) {
	root := writeProject(t, map[string]string{
		"suite.go": projectSource, "suite_test.go": "package suite\n\nimport \"testing\"\n\nfunc TestOk(t *testing.T) {}\n",
		"broken/broken_test.go": "package broken\n\nimport \"testing\"\n\nfunc TestX(t *testing.T) { undefined() }\n",
	})
	_, events, _ := runSuite(t, root, "")
	want := map[string]string{"suite/broken": "error", "suite_test.go::TestOk": "ok"}
	if asJSON(statuses(events)) != asJSON(want) {
		t.Errorf("statuses %v", statuses(events))
	}
}

func TestAPanicEndsTheRunWithItsTestInProgress(t *testing.T) {
	root := writeProject(t, map[string]string{"suite.go": projectSource, "suite_test.go": `package suite

import "testing"

func TestFirst(t *testing.T) {}

func TestPanics(t *testing.T) { panic("boom") }

func TestNever(t *testing.T) {}
`})
	code, events, stderr := runSuite(t, root, "")
	last := events[len(events)-1]
	if code != exitTestCrashed || last["event"] != "case_start" || last["case_id"] != "suite_test.go::TestPanics" {
		t.Errorf("exit %d, last event %v", code, last)
	}
	if !strings.Contains(stderr, "panic: boom") {
		t.Errorf("stderr %q", stderr)
	}
}

func TestARestartLeavesOutTheReportedTestsOfTheirPackageOnly(t *testing.T) {
	root := writeProject(t, map[string]string{"suite.go": projectSource,
		"suite_test.go":       "package suite\n\nimport \"testing\"\n\nfunc TestSame(t *testing.T) {}\n\nfunc TestNext(t *testing.T) {}\n",
		"other/other_test.go": "package other\n\nimport \"testing\"\n\nfunc TestSame(t *testing.T) {}\n",
	})
	_, events, _ := runSuite(t, root, `, "skip": ["suite_test.go::TestSame"]`)
	want := map[string]string{"other/other_test.go::TestSame": "ok", "suite_test.go::TestNext": "ok"}
	if asJSON(statuses(events)) != asJSON(want) {
		t.Errorf("statuses %v", statuses(events))
	}
}

func TestAnExcludedFileDoesNotRun(t *testing.T) {
	root := writeProject(t, map[string]string{"suite.go": projectSource, "suite_test.go": projectTestFile,
		"level_2_test.go": "package suite\n\nimport \"testing\"\n\nfunc TestLevel2(t *testing.T) { Missing() }\n"})
	_, events, _ := runSuite(t, root, `, "exclude": ["level_2_test.go"], "select": ["TestPasses"]`)
	want := map[string]string{"suite_test.go::TestPasses": "ok"}
	if asJSON(statuses(events)) != asJSON(want) {
		t.Errorf("statuses %v", statuses(events))
	}
}

func TestASuiteWithoutAModuleIsALoadError(t *testing.T) {
	_, events, _ := runSuite(t, t.TempDir(), "")
	if events[2]["event"] != "load_error" {
		t.Errorf("events %v", events)
	}
}

func TestACrashShowsTheProjectFramesOfItsPanic(t *testing.T) {
	r := newRecorded().feed(started("TestB"), out("TestB", "--- FAIL: TestB (0.00s)\n"),
		out("TestB", "panic: boom [recovered]\n"), out("TestB", "goroutine 7 [running]:\n"),
		out("TestB", "p.(*Bank).Deposit(...)\n"), out("TestB", "\t/ws/p/bank.go:14 +0x30\n"),
		out("TestB", "p_test.TestB(0x1?)\n"), out("TestB", "\t/ws/p/tests/b_test.go:9 +0x2c\n"),
		out("TestB", "testing.tRunner(0x1, 0x2)\n"), out("TestB", "\t/go/src/testing/testing.go:1 +0x1\n"),
		end("fail", "TestB"), testEvent{Action: "fail", Package: "p"})
	var stderr bytes.Buffer
	r.translator.conclude(&stderr)
	want := "tests/b_test.go:9 in TestB\nbank.go:14 in Bank.Deposit\npanic: boom [recovered]\n"
	if stderr.String() != want {
		t.Errorf("stderr %q", stderr.String())
	}
}
