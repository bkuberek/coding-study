package runner

import (
	"bufio"
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"io"
	"io/fs"
	"os"
	"os/exec"
	"path"
	"path/filepath"
	"regexp"
	"slices"
	"sort"
	"strings"
	"unicode"
	"unicode/utf8"
)

// A suite job runs a Go project's tests with `go test -json` in the project root, a child process
// of the runner in its process group, and reports each test (docs/specs/runners.md#go-project-jobs).
// The CLI sets the go command's environment, GOWORK included.

const (
	moduleFile      = "go.mod"
	testFileSuffix  = "_test.go"
	goFileSuffix    = ".go"
	allPackages     = "./..."
	goTestErrorType = "GoTestError"
	stderrTailLines = 20
	maxLineBytes    = 1 << 20
	// debugListenVariable names the address Delve listens on in a debug run; debugDelveVariable
	// the dlv binary, and debugPackageVariable the package directory to debug when the selections
	// name none.
	debugListenVariable  = "CSTUDY_GO_DEBUG_LISTEN"
	debugDelveVariable   = "CSTUDY_GO_DELVE"
	debugPackageVariable = "CSTUDY_GO_DEBUG_PACKAGE"
	delveReadyMarker     = "API server listening at:"
)

var moduleLine = regexp.MustCompile(`(?m)^module\s+"?([^"\s]+)"?`)

// projectTests knows a project's packages and which file declares each top-level test.
type projectTests struct {
	module string
	// files maps a package directory, relative to the root, to its top-level tests' files.
	files map[string]map[string]string
	// directories are the package directories holding Go files, in order.
	directories []string
}

func (p *projectTests) id(importPath, name string) string {
	top, _, _ := strings.Cut(name, "/")
	if file, ok := p.files[p.directory(importPath)][top]; ok {
		return file + idSeparator + name
	}
	return importPath + idSeparator + name
}

func (p *projectTests) directory(importPath string) string {
	if importPath == p.module {
		return "."
	}
	return strings.TrimPrefix(importPath, p.module+"/")
}

func (p *projectTests) importPath(directory string) string {
	if directory == "." {
		return p.module
	}
	return p.module + "/" + directory
}

// scanProject parses the root's test files, those of exclude left out, as `./...` would find
// them: no directory named testdata or vendor or starting with . or _, and no nested module.
func scanProject(root string, exclude map[string]bool) (*projectTests, error) {
	module, err := os.ReadFile(filepath.Join(root, moduleFile))
	if err != nil {
		return nil, err
	}
	found := moduleLine.FindSubmatch(module)
	if found == nil {
		return nil, fmt.Errorf("%s declares no module", moduleFile)
	}
	tests := &projectTests{module: string(found[1]), files: map[string]map[string]string{}}
	seen := map[string]bool{}
	err = filepath.WalkDir(root, func(file string, entry fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		relative, _ := filepath.Rel(root, file)
		relative = filepath.ToSlash(relative)
		if entry.IsDir() {
			return skippedDirectory(root, file, entry.Name())
		}
		if !strings.HasSuffix(relative, goFileSuffix) || exclude[relative] {
			return nil
		}
		directory := path.Dir(relative)
		if !seen[directory] {
			seen[directory] = true
			tests.directories = append(tests.directories, directory)
		}
		if strings.HasSuffix(relative, testFileSuffix) {
			tests.add(directory, relative, file)
		}
		return nil
	})
	sort.Strings(tests.directories)
	return tests, err
}

func skippedDirectory(root, file, name string) error {
	if file == root {
		return nil
	}
	nested := false
	if _, err := os.Stat(filepath.Join(file, moduleFile)); err == nil {
		nested = true
	}
	if nested || name == "testdata" || name == "vendor" || strings.HasPrefix(name, ".") ||
		strings.HasPrefix(name, "_") {
		return filepath.SkipDir
	}
	return nil
}

// add records the top-level tests a test file declares; a file that does not parse still
// declares those the parser read before the error.
func (p *projectTests) add(directory, relative, file string) {
	parsed, _ := parser.ParseFile(token.NewFileSet(), file, nil, parser.SkipObjectResolution)
	if parsed == nil {
		return
	}
	for _, declaration := range parsed.Decls {
		function, ok := declaration.(*ast.FuncDecl)
		if !ok || function.Recv != nil || !isTestFunction(function.Name.Name) {
			continue
		}
		if p.files[directory] == nil {
			p.files[directory] = map[string]string{}
		}
		p.files[directory][function.Name.Name] = relative
	}
}

// isTestFunction tells the functions `go test` runs as tests: TestXxx (not TestMain), FuzzXxx and
// examples.
func isTestFunction(name string) bool {
	if strings.HasPrefix(name, "Example") {
		return true
	}
	for _, prefix := range []string{"Test", "Fuzz"} {
		rest, ok := strings.CutPrefix(name, prefix)
		if ok && name != "TestMain" {
			first, _ := utf8.DecodeRuneInString(rest)
			return rest == "" || !unicode.IsLower(first)
		}
	}
	return false
}

// goTestRun is one `go test` over some packages, leaving out some top-level tests.
type goTestRun struct {
	patterns []string
	skip     []string
}

// suiteRequest is a suite job's request, read in the project's terms.
type suiteRequest struct {
	root    string
	exclude map[string]bool
	// run names the selected top-level tests; empty runs every test.
	run []string
	// onlyIn holds the packages of the selections when every selection names a file.
	onlyIn map[string]bool
	// skipIn holds the top-level tests to leave out of each package.
	skipIn map[string][]string
	// leftOut holds the packages reported whole, as a package that did not build is.
	leftOut map[string]bool
}

func readSuiteRequest(j *job, tests *projectTests) *suiteRequest {
	request := &suiteRequest{root: j.Root, exclude: excluded(j.Exclude),
		skipIn: map[string][]string{}, leftOut: map[string]bool{}}
	byFile := true
	for _, selection := range j.Select {
		file, name, named := strings.Cut(selection, idSeparator)
		if !named {
			name, byFile = selection, false
		} else if request.onlyIn == nil {
			request.onlyIn = map[string]bool{}
		}
		top, _, _ := strings.Cut(name, "/")
		request.run = appendOnce(request.run, top)
		if named {
			request.onlyIn[testDirectory(file, tests)] = true
		}
	}
	if !byFile {
		request.onlyIn = nil
	}
	for _, id := range j.Skip {
		file, name, named := strings.Cut(id, idSeparator)
		if !named {
			request.leftOut[tests.directory(id)] = true
			continue
		}
		top, _, _ := strings.Cut(name, "/")
		directory := testDirectory(file, tests)
		request.skipIn[directory] = appendOnce(request.skipIn[directory], top)
	}
	return request
}

func excluded(paths []string) map[string]bool {
	found := map[string]bool{}
	for _, file := range paths {
		found[file] = true
	}
	return found
}

// testDirectory is the package directory of an id's file part: a file, or an import path.
func testDirectory(file string, tests *projectTests) string {
	if strings.HasSuffix(file, goFileSuffix) {
		return path.Dir(file)
	}
	return tests.directory(file)
}

func appendOnce(items []string, item string) []string {
	if slices.Contains(items, item) {
		return items
	}
	return append(items, item)
}

// runs are the `go test` runs of the request: one over every package, or, after a restart, one
// for the packages without tests to leave out and one for each package with some, so that a test
// named like one reported in another package still runs.
func (r *suiteRequest) runs(tests *projectTests) []goTestRun {
	if len(r.skipIn) == 0 && len(r.leftOut) == 0 && r.onlyIn == nil {
		return []goTestRun{{patterns: []string{allPackages}}}
	}
	var together goTestRun
	var apart []goTestRun
	for _, directory := range tests.directories {
		if r.leftOut[directory] || r.onlyIn != nil && !r.onlyIn[directory] {
			continue
		}
		pattern := packagePattern(directory)
		if skip := r.skipIn[directory]; len(skip) > 0 {
			apart = append(apart, goTestRun{patterns: []string{pattern}, skip: skip})
		} else {
			together.patterns = append(together.patterns, pattern)
		}
	}
	if len(together.patterns) > 0 {
		apart = append([]goTestRun{together}, apart...)
	}
	return apart
}

// flags are the go test flags of the request, without the packages; prefix is "" for `go test`
// and "test." for a test binary.
func (r *suiteRequest) flags(skip []string, prefix string) []string {
	var flags []string
	if len(r.run) > 0 {
		flags = append(flags, "-"+prefix+"run", namesPattern(r.run))
	}
	if len(skip) > 0 {
		flags = append(flags, "-"+prefix+"skip", namesPattern(skip))
	}
	return flags
}

func namesPattern(names []string) string {
	quoted := make([]string, len(names))
	for i, name := range names {
		quoted[i] = regexp.QuoteMeta(name)
	}
	return "^(" + strings.Join(quoted, "|") + ")$"
}

// overlay writes the go command's overlay that removes the excluded files, and returns its path;
// "" when nothing is excluded.
func (r *suiteRequest) overlay() (string, error) {
	if len(r.exclude) == 0 {
		return "", nil
	}
	replace := map[string]string{}
	for file := range r.exclude {
		replace[filepath.Join(r.root, filepath.FromSlash(file))] = ""
	}
	document, err := json.Marshal(map[string]any{"Replace": replace})
	if err != nil {
		return "", err
	}
	file, err := os.CreateTemp("", "cs-go-suite-overlay-*.json")
	if err != nil {
		return "", err
	}
	defer file.Close()
	_, err = file.Write(document)
	return file.Name(), err
}

// runSuiteJob reports every test of the project (docs/specs/runners.md#go-project-jobs). It
// returns false when a test never ended: the runner then exits without bye.
func runSuiteJob(j *job, events *writer, stderr io.Writer) bool {
	events.jobStart(j.JobID)
	tests, err := scanProject(j.Root, excluded(j.Exclude))
	if err != nil {
		events.loadError(j.JobID, &userError{Type: goTestErrorType, Message: err.Error()})
		events.jobEnd(j.JobID)
		return true
	}
	request := readSuiteRequest(j, tests)
	translator := newTranslator(j.JobID, j.Root, events, tests, j.Skip)
	overlay, err := request.overlay()
	if overlay != "" {
		defer os.Remove(overlay)
	}
	if err == nil && os.Getenv(debugListenVariable) != "" {
		err = runDebugged(request, tests, overlay, translator)
	} else if err == nil {
		err = runEach(request, tests, overlay, translator)
	}
	if err != nil {
		events.loadError(j.JobID, &userError{Type: goTestErrorType, Message: err.Error()})
		events.jobEnd(j.JobID)
		return true
	}
	return translator.conclude(stderr)
}

// runEach runs the request's `go test` runs, then each package whose test binary ended early again
// without the tests reported so far, until none ends early: every run reports the test it ended
// in, so each package runs at most once per top-level test.
func runEach(request *suiteRequest, tests *projectTests, overlay string, t *translator) error {
	runs := request.runs(tests)
	for len(runs) > 0 {
		for _, run := range runs {
			if err := runGoTest(request, overlay, run, t); err != nil {
				return err
			}
		}
		runs = nil
		for _, importPath := range t.takeReruns() {
			directory := tests.directory(importPath)
			skip := append(slices.Clone(request.skipIn[directory]), t.reportedTops[importPath]...)
			runs = append(runs, goTestRun{patterns: []string{packagePattern(directory)}, skip: skip})
		}
	}
	return nil
}

func runGoTest(request *suiteRequest, overlay string, run goTestRun, t *translator) error {
	arguments := []string{"test", "-json", "-count=1", "-timeout=0"}
	if overlay != "" {
		arguments = append(arguments, "-overlay="+overlay)
	}
	arguments = append(append(arguments, request.flags(run.skip, "")...), run.patterns...)
	command := exec.Command("go", arguments...)
	command.Dir = request.root
	return follow(command, t)
}

// follow runs a command whose standard output is `go test -json` events; an error when it failed
// before any package ran.
func follow(command *exec.Cmd, t *translator) error {
	var errors tail
	command.Stderr = &errors
	output, err := command.StdoutPipe()
	if err != nil {
		return err
	}
	if err := command.Start(); err != nil {
		return err
	}
	t.follow(lines(output), quietGap)
	waited := command.Wait()
	t.endRun()
	if waited != nil && !t.sawPackage {
		return fmt.Errorf("%s: %v\n%s", strings.Join(command.Args, " "), waited, errors.String())
	}
	return nil
}

// lines sends the reader's lines, each a copy, until it ends.
func lines(reader io.Reader) <-chan []byte {
	sent := make(chan []byte)
	go func() {
		defer close(sent)
		scanner := bufio.NewScanner(reader)
		scanner.Buffer(nil, maxLineBytes)
		for scanner.Scan() {
			sent <- slices.Clone(scanner.Bytes())
		}
	}()
	return sent
}

// tail keeps the last lines written to it.
type tail struct{ kept []string }

func (t *tail) Write(data []byte) (int, error) {
	t.kept = append(t.kept, strings.SplitAfter(string(data), "\n")...)
	if len(t.kept) > stderrTailLines {
		t.kept = t.kept[len(t.kept)-stderrTailLines:]
	}
	return len(data), nil
}

func (t *tail) String() string { return strings.TrimRight(strings.Join(t.kept, ""), "\n") }
