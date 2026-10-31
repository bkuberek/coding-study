// Package runner is the Go runner (docs/specs/runners.md). The CLI generates a main package
// that links the user's package and the reference packages, each with a generated registration
// file, and calls Main with their registrations:
//
//	runner.Main(runner.Registry{"user": two_sum.CsTargets, "ref/hash-map": hash_map.CsTargets}, nil, nil)
//
// A suite job needs no target: it runs a project's tests with `go test` (suite.go).
//
// Exit codes: 0 once `bye` is written; 2 for a request that cannot be run; 3 after
// `restart_requested`; 1 after a test crashed its test binary, with that test in progress.
package runner

import (
	"flag"
	"fmt"
	"io"
	"os"
)

const (
	exitCompleted  = 0
	exitBadRequest = 2
	// exitRestart follows restart_requested: a stress run left worker goroutines running.
	exitRestart = 3
	// exitTestCrashed leaves the test that crashed its test binary in progress, for the CLI to
	// report as a crash.
	exitTestCrashed = 1
)

// Main runs the request named on the command line and exits. A class kind's packages also
// offer thunks, the typed method callers of their generated thunk file.
func Main(registry Registry, unavailable Unavailable, thunks Thunks) {
	keepCrashOutput()
	os.Exit(run(&loader{registry: registry, unavailable: unavailable, thunks: thunks}, os.Args[1:], os.Stderr))
}

// suiteJob is the request's suite job, which comes alone; nil for any other request.
func suiteJob(req *request) *job {
	if len(req.Jobs) == 1 && req.Jobs[0].Kind == kindSuite {
		return &req.Jobs[0]
	}
	return nil
}

// MainBuildFailed runs the request of a project whose code did not compile: every job that loads
// target reports a load_error of type CompileError with the compiler's lines as its message and
// the first error's place as its trace.
func MainBuildFailed(target, message, trace string) {
	keepCrashOutput()
	failure := &userError{Type: compileErrorType, Message: message, Trace: trace}
	os.Exit(run(&loader{broken: map[string]*userError{target: failure}}, os.Args[1:], os.Stderr))
}

func run(l *loader, argv []string, stderr io.Writer) int {
	flags := flag.NewFlagSet("cs-go-runner", flag.ContinueOnError)
	flags.SetOutput(stderr)
	requestPath := flags.String("request", "", "request file (JSON)")
	outPath := flags.String("out", "", "event file to write (JSON Lines)")
	if err := flags.Parse(argv); err != nil || *requestPath == "" || *outPath == "" {
		fmt.Fprintln(stderr, "usage: cs-go-runner --request R --out O")
		return exitBadRequest
	}
	out, err := os.Create(*outPath)
	if err != nil {
		fmt.Fprintln(stderr, "cs-go-runner:", err)
		return exitBadRequest
	}
	defer out.Close()
	events := &writer{out: out}
	events.hello()
	req, err := readRequest(*requestPath)
	if err != nil {
		fmt.Fprintln(stderr, "cs-go-runner: bad request:", err)
		return exitBadRequest
	}
	if suite := suiteJob(req); suite != nil {
		if !runSuiteJob(suite, events, stderr) {
			return exitTestCrashed
		}
	} else if req.Mode == modeBench {
		runBenchJobs(l, req.Jobs, events)
	} else if !runTestJobs(l, req.Jobs, events) {
		return exitRestart
	}
	events.bye()
	return exitCompleted
}
