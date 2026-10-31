package runner

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"strings"
	"time"
)

// A suite job's results (docs/specs/runners.md#go-project-jobs). `go test -json` runs packages
// side by side and t.Parallel tests together, while the protocol has one test in progress, so a
// test's case_start and case_result are written together once it ends. When no event comes for
// quietGap, the earliest started test still running is named in progress with case_start, so the
// CLI's hang guard times it from there; results that end meanwhile wait for its own. A test binary
// that ends without its closing PASS or FAIL line (a panic, os.Exit, a fatal runtime error) is an
// error of the test it ended in, and its package runs again without the tests reported so far.

const (
	statusFailed  = "failed"
	statusSkipped = "skipped"
	// quietGap is how long `go test` stays silent before a running test is named in progress.
	quietGap = time.Second
	// compileErrorType is a package that does not compile or does not pass go vet.
	compileErrorType = "CompileError"
	// binaryExitedType is a test binary that ended outside any test.
	binaryExitedType = "TestBinaryExited"
	// exitType is a test that ended its test binary without a panic: os.Exit, log.Fatal.
	exitType       = "exit"
	idSeparator    = "::"
	crashTextLines = 30
)

// testEvent is one line of `go test -json` (go doc cmd/test2json). OutputType is left out: older
// releases do not write it.
type testEvent struct {
	Action      string
	Package     string
	Test        string
	Output      string
	Elapsed     float64
	ImportPath  string
	FailedBuild string
}

// suiteResult is a suite test's case_result: ok, failed, skipped or error.
type suiteResult struct {
	status     string
	message    string
	err        *userError
	durationNS int64
	stdout     string
}

func (r suiteResult) fields() []field {
	fields := []field{{"status", r.status}}
	switch r.status {
	case statusFailed, statusSkipped:
		fields = append(fields, field{"message", r.message})
	case statusError:
		fields = append(fields, field{"error", r.err})
	}
	fields = append(fields, field{"duration_ns", r.durationNS})
	if r.stdout != "" {
		fields = append(fields, field{"stdout", r.stdout})
	}
	return fields
}

func (w *writer) suiteResult(jobID, caseID string, r suiteResult) {
	w.emit(append([]field{{"event", "case_result"}, {"job_id", jobID}, {"case_id", caseID}},
		r.fields()...)...)
}

// testNames tells a test's id: the file that declares its top-level test, and its name.
type testNames interface {
	id(importPath, name string) string
}

type runningTest struct {
	pkg    *packageRun
	name   string
	id     string
	seq    int
	paused bool
	done   bool
	parent *runningTest
	// open counts the subtests that started and have not ended.
	open   int
	output []string
}

func (t *runningTest) leaf() bool { return !t.done && !t.paused && t.open == 0 }

type packageRun struct {
	importPath string
	tests      map[string]*runningTest
	output     []string
	// closed is set by the test binary's own closing PASS or FAIL line: it did not end early.
	closed bool
	// panicked are failed tests whose output holds a panic, held until the package ends: the
	// binary ended in them, unless it went on to close normally.
	panicked []*runningTest
}

type readyResult struct {
	id     string
	result suiteResult
	// pkg and top are the import path and the top-level test of a test's result; top is empty
	// for a package's.
	pkg, top string
}

// translator turns the events of one or more `go test -json` runs into the job's events.
type translator struct {
	jobID string
	// root is the project root, whose files' frames a crash shows.
	root       string
	events     *writer
	names      testNames
	reported   map[string]bool
	packages   map[string]*packageRun
	builds     map[string][]string
	failed     map[string]bool
	seq        int
	ready      []readyResult
	inProgress *runningTest
	// reruns are the packages whose test binary ended early, to run again.
	reruns map[string]bool
	// reportedTops are the top-level tests reported, by import path.
	reportedTops map[string][]string
	// sawPackage is set once any package started, built or failed to build.
	sawPackage bool
}

func newTranslator(jobID, root string, events *writer, names testNames, skip []string) *translator {
	reported := map[string]bool{}
	for _, id := range skip {
		reported[id] = true
	}
	return &translator{jobID: jobID, root: root, events: events, names: names, reported: reported,
		packages: map[string]*packageRun{}, builds: map[string][]string{}, failed: map[string]bool{},
		reruns: map[string]bool{}, reportedTops: map[string][]string{}}
}

// follow handles the lines of one `go test -json` run until they end, naming a test in progress
// whenever the run stays silent for quiet.
func (t *translator) follow(lines <-chan []byte, quiet time.Duration) {
	timer := time.NewTimer(quiet)
	defer timer.Stop()
	for {
		select {
		case line, ok := <-lines:
			if !ok {
				return
			}
			var event testEvent
			if json.Unmarshal(line, &event) == nil {
				t.handle(event)
			}
			if !timer.Stop() {
				select {
				case <-timer.C:
				default:
				}
			}
			timer.Reset(quiet)
		case <-timer.C:
			t.quiet()
		}
	}
}

func (t *translator) handle(e testEvent) {
	switch e.Action {
	case "build-output":
		t.sawPackage = true
		t.builds[e.ImportPath] = append(t.builds[e.ImportPath], e.Output)
	case "build-fail":
		t.sawPackage = true
		t.failed[e.ImportPath] = true
	case "start":
		t.sawPackage = true
		t.pkg(e.Package)
	case "run":
		t.run(e)
	case "pause", "cont":
		if test := t.pkg(e.Package).tests[e.Test]; test != nil {
			test.paused = e.Action == "pause"
		}
	case "output":
		t.output(e)
	case "pass", "fail", "skip":
		if e.Test == "" {
			t.packageEnd(e)
		} else {
			t.testEnd(e)
		}
	}
	t.pump()
}

func (t *translator) pkg(importPath string) *packageRun {
	p := t.packages[importPath]
	if p == nil {
		p = &packageRun{importPath: importPath, tests: map[string]*runningTest{}}
		t.packages[importPath] = p
	}
	return p
}

func (t *translator) run(e testEvent) {
	p := t.pkg(e.Package)
	t.seq++
	test := &runningTest{pkg: p, name: e.Test, id: t.names.id(e.Package, e.Test), seq: t.seq}
	if slash := strings.LastIndex(e.Test, "/"); slash >= 0 {
		test.parent = p.tests[e.Test[:slash]]
	}
	if test.parent != nil {
		test.parent.open++
	}
	p.tests[e.Test] = test
}

func (t *translator) output(e testEvent) {
	p := t.pkg(e.Package)
	if test := p.tests[e.Test]; e.Test != "" && test != nil {
		test.output = append(test.output, e.Output)
		return
	}
	p.output = append(p.output, e.Output)
	if line := strings.TrimSpace(e.Output); line == "PASS" || line == "FAIL" {
		p.closed = true
	}
}

func (t *translator) testEnd(e testEvent) {
	test := t.pkg(e.Package).tests[e.Test]
	if test == nil || test.done {
		return
	}
	test.done = true
	if test.parent != nil {
		test.parent.open--
	}
	duration := int64(e.Elapsed * float64(time.Second))
	lines := unframed(test.output)
	switch e.Action {
	case "pass":
		text := strings.Join(lines, "")
		t.queueTest(test, suiteResult{status: statusOK, durationNS: duration,
			stdout: truncated([]byte(text), len(text))})
	case "skip":
		t.queueTest(test, suiteResult{status: statusSkipped, durationNS: duration,
			message: messageOf(lines, "skipped")})
	default:
		if panicLine(lines) != "" {
			test.pkg.panicked = append(test.pkg.panicked, test)
			return
		}
		t.queueTest(test, failure(test, duration))
	}
}

func failure(test *runningTest, duration int64) suiteResult {
	return suiteResult{status: statusFailed, durationNS: duration,
		message: messageOf(unframed(test.output), "failed")}
}

func (t *translator) packageEnd(e testEvent) {
	p := t.pkg(e.Package)
	switch {
	case e.FailedBuild != "":
		t.queue(readyResult{id: p.importPath, pkg: p.importPath, result: compileError(t.builds[e.FailedBuild])})
		delete(t.failed, e.FailedBuild)
	case e.Action == "skip":
	case !p.closed:
		t.ended(p)
	default:
		for _, test := range p.panicked {
			t.queueTest(test, failure(test, 0))
		}
	}
	p.panicked = nil
}

// ended reports a test binary that ended early as an error of its culprit: the test named in
// progress if it was there, else the test that panicked, else the one still running. Other panics
// are failures. The package runs again without the tests reported so far.
func (t *translator) ended(p *packageRun) {
	culprit := t.inProgress
	if culprit == nil || culprit.pkg != p || culprit.done && !contains(p.panicked, culprit) {
		culprit = nil
	}
	if culprit == nil && len(p.panicked) > 0 {
		culprit = p.panicked[len(p.panicked)-1]
	}
	if culprit == nil {
		culprit = earliest(p, func(test *runningTest) bool { return !test.done && !test.paused })
	}
	for _, test := range p.panicked {
		if test != culprit {
			t.queueTest(test, failure(test, 0))
		}
	}
	if culprit == nil {
		message := messageOf(unframed(p.output), "the test binary ended outside any test")
		t.queue(readyResult{id: p.importPath, pkg: p.importPath, result: suiteResult{
			status: statusError, err: &userError{Type: binaryExitedType, Message: message}}})
		return
	}
	culprit.done = true
	t.queueTest(culprit, binaryEnded(culprit, t.root))
	t.reruns[p.importPath] = true
}

// takeReruns are the packages to run again, in order; it forgets them.
func (t *translator) takeReruns() []string {
	packages := make([]string, 0, len(t.reruns))
	for importPath := range t.reruns {
		packages = append(packages, importPath)
	}
	slices.Sort(packages)
	t.reruns = map[string]bool{}
	return packages
}

func contains(tests []*runningTest, wanted *runningTest) bool {
	for _, test := range tests {
		if test == wanted {
			return true
		}
	}
	return false
}

// earliest is the first started test of p that matches, or nil.
func earliest(p *packageRun, matches func(*runningTest) bool) *runningTest {
	var found *runningTest
	for _, test := range p.tests {
		if matches(test) && (found == nil || test.seq < found.seq) {
			found = test
		}
	}
	return found
}

// quiet names the earliest started test still running in progress, when nothing else is.
func (t *translator) quiet() {
	if t.inProgress != nil || len(t.ready) > 0 {
		return
	}
	var found *runningTest
	for _, p := range t.packages {
		candidate := earliest(p, func(test *runningTest) bool {
			return test.leaf() && !t.reported[test.id]
		})
		if candidate != nil && (found == nil || candidate.seq < found.seq) {
			found = candidate
		}
	}
	if found != nil {
		t.events.caseStart(t.jobID, found.id)
		t.inProgress = found
	}
}

func (t *translator) queue(ready readyResult) { t.ready = append(t.ready, ready) }

func (t *translator) queueTest(test *runningTest, result suiteResult) {
	top, _, _ := strings.Cut(test.name, "/")
	t.queue(readyResult{id: test.id, result: result, pkg: test.pkg.importPath, top: top})
}

// pump writes the results that are ready: the one in progress first, the others only when no
// test is in progress.
func (t *translator) pump() {
	if t.inProgress != nil {
		index := -1
		for i, ready := range t.ready {
			if ready.id == t.inProgress.id {
				index = i
			}
		}
		if index < 0 {
			return
		}
		t.write(t.ready[index])
		t.ready = append(t.ready[:index], t.ready[index+1:]...)
		t.inProgress = nil
	}
	for _, ready := range t.ready {
		if !t.reported[ready.id] {
			t.events.caseStart(t.jobID, ready.id)
			t.write(ready)
		}
	}
	t.ready = t.ready[:0]
}

func (t *translator) write(ready readyResult) {
	t.events.suiteResult(t.jobID, ready.id, ready.result)
	t.reported[ready.id] = true
	if ready.top != "" {
		t.reportedTops[ready.pkg] = appendOnce(t.reportedTops[ready.pkg], ready.top)
	}
}

// endRun reports the packages whose build failed with no package event to say so.
func (t *translator) endRun() {
	for importPath := range t.failed {
		bare := bareImportPath(importPath)
		t.queue(readyResult{id: bare, pkg: bare, result: compileError(t.builds[importPath])})
	}
	t.failed = map[string]bool{}
	t.pump()
}

// conclude ends the job with job_end; or, when the test in progress never ended (`go test` itself
// was ended), it leaves that test in progress with its output on stderr, for the CLI to report as a
// crash, and returns false: the runner exits without bye.
func (t *translator) conclude(stderr io.Writer) bool {
	if t.inProgress != nil {
		fmt.Fprint(stderr, crashText(t.inProgress, t.root))
		return false
	}
	t.events.jobEnd(t.jobID)
	return true
}

var framingLine = regexp.MustCompile(`^\s*(=== (RUN|PAUSE|CONT|NAME)|--- (PASS|FAIL|SKIP):)`)

// unframed are a test's output lines without the framing `go test -v` writes around them.
func unframed(lines []string) []string {
	var kept []string
	for _, line := range lines {
		if !framingLine.MatchString(line) {
			kept = append(kept, line)
		}
	}
	return kept
}

// messageOf is the lines without their common indentation and the final newline, or fallback
// when there are none.
func messageOf(lines []string, fallback string) string {
	indent := -1
	for _, line := range lines {
		if strings.TrimSpace(line) == "" {
			continue
		}
		width := len(line) - len(strings.TrimLeft(line, " \t"))
		if indent < 0 || width < indent {
			indent = width
		}
	}
	var text strings.Builder
	for _, line := range lines {
		if len(line) >= indent && indent > 0 {
			line = line[indent:]
		}
		text.WriteString(line)
	}
	message := strings.TrimRight(text.String(), "\n")
	if message == "" {
		return fallback
	}
	return message
}

// panicLine is the first line a panic or a fatal runtime error wrote, or "".
func panicLine(lines []string) string {
	for _, line := range lines {
		if strings.HasPrefix(line, "panic: ") || strings.HasPrefix(line, "fatal error: ") {
			return strings.TrimRight(line, "\n")
		}
	}
	return ""
}

// binaryEnded is the error of a test its test binary ended in: a panic or a fatal runtime error,
// with the frames of the project's files as its trace, or an exit; what the test printed before is
// its output.
func binaryEnded(test *runningTest, root string) suiteResult {
	lines := unframed(test.output)
	why := panicLine(lines)
	var printed []string
	for _, line := range lines {
		if why != "" && strings.HasPrefix(line, why) {
			break
		}
		printed = append(printed, line)
	}
	stdout := strings.Join(printed, "")
	failure := &userError{Type: exitType,
		Message: fmt.Sprintf("the test binary ended during %s: os.Exit or log.Fatal ends it", test.name)}
	if why != "" {
		kind, message, _ := strings.Cut(why, ": ")
		message, _, _ = strings.Cut(message, " [recovered")
		failure = &userError{Type: kind, Message: message,
			Trace: strings.Join(projectFrames(lines, root), "\n")}
	}
	return suiteResult{status: statusError, err: failure, stdout: truncated([]byte(stdout), len(stdout))}
}

// crashText is why the test binary ended, closing what the test printed before: the panic, after
// the frames of the project's files in its stack (innermost last, `bank.go:14 in Bank.Deposit`),
// or the test's last lines and that the binary ended during it.
func crashText(test *runningTest, root string) string {
	lines := unframed(test.output)
	why := panicLine(lines)
	if why == "" {
		if len(lines) > crashTextLines {
			lines = lines[len(lines)-crashTextLines:]
		}
		why = fmt.Sprintf("the test binary of %s ended during %s", test.pkg.importPath, test.name)
		return strings.Join(lines, "") + why + "\n"
	}
	var kept []string
	for _, line := range lines {
		if strings.HasPrefix(line, why) {
			break
		}
		kept = append(kept, line)
	}
	for _, frame := range projectFrames(lines, root) {
		kept = append(kept, frame+"\n")
	}
	return strings.Join(kept, "") + why + "\n"
}

// projectFrames are the frames of a Go stack trace in files under root, innermost last, at most
// maxTraceLines.
func projectFrames(lines []string, root string) []string {
	var frames []string
	for i := 1; i < len(lines) && root != ""; i++ {
		place, _, _ := strings.Cut(strings.TrimSpace(lines[i]), " +")
		file, number, found := cutLast(place, ":")
		relative, inRoot := underRoot(file, root)
		if !strings.HasPrefix(lines[i], "\t") || !found || !inRoot {
			continue
		}
		frames = append(frames, fmt.Sprintf("%s:%s in %s", filepath.ToSlash(relative), number,
			frameFunction(strings.TrimSpace(lines[i-1]))))
	}
	slices.Reverse(frames)
	if len(frames) > maxTraceLines {
		frames = frames[len(frames)-maxTraceLines:]
	}
	return frames
}

// frameFunction is a stack frame's function without its package and arguments:
// `bank-project-go.(*Bank).Deposit(...)` is `Bank.Deposit`.
func frameFunction(call string) string {
	function, _, _ := cutLast(call, "(")
	if slash := strings.LastIndex(function, "/"); slash >= 0 {
		function = function[slash+1:]
	}
	_, function, _ = strings.Cut(function, ".")
	return readableFunction(function)
}

// underRoot is file relative to root, which a stack names as given or with its links resolved.
func underRoot(file, root string) (string, bool) {
	roots := []string{root}
	if resolved, err := filepath.EvalSymlinks(root); err == nil && resolved != root {
		roots = append(roots, resolved)
	}
	for _, candidate := range roots {
		if relative, ok := strings.CutPrefix(file, candidate+string(os.PathSeparator)); ok {
			return relative, true
		}
	}
	return "", false
}

func cutLast(text, separator string) (string, string, bool) {
	index := strings.LastIndex(text, separator)
	if index < 0 {
		return text, "", false
	}
	return text[:index], text[index+len(separator):], true
}

var diagnosticPlace = regexp.MustCompile(`^(?:\./)?([^\s:]+\.go):(\d+)`)

// compileError is a package's build output without its `#` headers, the paths relative to the
// root; its trace names the first error's place.
func compileError(output []string) suiteResult {
	var lines []string
	trace := ""
	for _, line := range output {
		if strings.HasPrefix(line, "#") {
			continue
		}
		line = strings.TrimPrefix(line, "./")
		if place := diagnosticPlace.FindStringSubmatch(line); place != nil && trace == "" {
			trace = place[1] + ":" + place[2]
		}
		lines = append(lines, line)
	}
	message := messageOf(lines, "the package does not build")
	return suiteResult{status: statusError,
		err: &userError{Type: compileErrorType, Message: message, Trace: trace}}
}

// bareImportPath drops the test binary a build names after the package: `bank [bank.test]`.
func bareImportPath(importPath string) string {
	path, _, _ := strings.Cut(importPath, " ")
	return path
}
