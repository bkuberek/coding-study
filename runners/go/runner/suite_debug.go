package runner

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// debugBinary is the test binary of a debug run, next to the runner's own private copy, so the
// CLI ends it with the run however the run ends.
const debugBinary = "debug.test"

// runDebugged runs one package's tests under Delve (docs/specs/runners.md#go-project-jobs): its
// test binary, built without optimizations or inlining, under `dlv exec --headless`, its output
// through `go tool test2json`. Delve's ready line goes to the runner's standard output, where the
// CLI looks for it.
func runDebugged(request *suiteRequest, tests *projectTests, overlay string, t *translator) error {
	directory := debugDirectory(request, tests)
	runner, err := os.Executable()
	if err != nil {
		return err
	}
	binary := filepath.Join(filepath.Dir(runner), debugBinary)
	built, err := buildDebugBinary(request.root, directory, overlay, binary)
	if err != nil {
		return err
	}
	if built != nil {
		importPath := tests.importPath(directory)
		t.queue(readyResult{id: importPath, pkg: importPath, result: *built})
		t.pump()
		return nil
	}
	if _, err := os.Stat(binary); err != nil {
		return nil
	}
	arguments := []string{"exec", "--headless", "--listen=" + os.Getenv(debugListenVariable),
		"--api-version=2", "--wd", filepath.Join(request.root, directory), binary, "--",
		"-test.v=test2json", "-test.count=1", "-test.timeout=0", "-test.paniconexit0"}
	arguments = append(arguments, request.flags(request.skipIn[directory], "test.")...)
	debugger := exec.Command(os.Getenv(debugDelveVariable), arguments...)
	debugger.Dir = request.root
	debugger.Stderr = os.Stderr
	converter := exec.Command("go", "tool", "test2json", "-t", "-p", tests.importPath(directory))
	converter.Stderr = os.Stderr
	return followDebugged(debugger, converter, t)
}

// buildDebugBinary builds the package's test binary; a result to report when it does not build.
func buildDebugBinary(root, directory, overlay, binary string) (*suiteResult, error) {
	arguments := []string{"test", "-c", "-o", binary, "-gcflags=all=-N -l"}
	if overlay != "" {
		arguments = append(arguments, "-overlay="+overlay)
	}
	command := exec.Command("go", append(arguments, packagePattern(directory))...)
	command.Dir = root
	output, err := command.CombinedOutput()
	if err == nil {
		return nil, nil
	}
	lines := strings.SplitAfter(string(output), "\n")
	if !diagnosticPlace.MatchString(strings.TrimPrefix(firstUnheaded(lines), "./")) {
		return nil, fmt.Errorf("go test -c: %v\n%s", err, output)
	}
	result := compileError(lines)
	return &result, nil
}

func firstUnheaded(lines []string) string {
	for _, line := range lines {
		if !strings.HasPrefix(line, "#") {
			return line
		}
	}
	return ""
}

func followDebugged(debugger, converter *exec.Cmd, t *translator) error {
	debuggerOutput, err := debugger.StdoutPipe()
	if err != nil {
		return err
	}
	converterInput, err := converter.StdinPipe()
	if err != nil {
		return err
	}
	events, err := converter.StdoutPipe()
	if err != nil {
		return err
	}
	if err := converter.Start(); err != nil {
		return err
	}
	if err := debugger.Start(); err != nil {
		return err
	}
	go forward(debuggerOutput, converterInput, os.Stdout)
	t.follow(lines(events), quietGap)
	_ = debugger.Wait()
	_ = converter.Wait()
	t.endRun()
	return nil
}

// forward copies the debugger's output to test2json, except its ready line, which goes to ready.
func forward(output io.Reader, converter io.WriteCloser, ready io.Writer) {
	defer converter.Close()
	scanner := bufio.NewScanner(output)
	scanner.Buffer(nil, maxLineBytes)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.Contains(line, delveReadyMarker) {
			fmt.Fprintln(ready, line)
			continue
		}
		fmt.Fprintln(converter, line)
	}
}

// debugDirectory is the package a debug run debugs: that of the selections when they name files
// of one package, else the one the CLI names (the generated test files'), else the first with
// tests.
func debugDirectory(request *suiteRequest, tests *projectTests) string {
	if len(request.onlyIn) == 1 {
		for directory := range request.onlyIn {
			return directory
		}
	}
	if named := os.Getenv(debugPackageVariable); named != "" {
		return named
	}
	for _, directory := range tests.directories {
		if len(tests.files[directory]) > 0 {
			return directory
		}
	}
	return "."
}

func packagePattern(directory string) string {
	if directory == "." {
		return "."
	}
	return "./" + directory
}
