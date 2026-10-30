// Package runner is the Go runner (docs/specs/runners.md). The CLI generates a main package
// that links the user's package and the reference packages, each with a generated registration
// file, and calls Main with their registrations:
//
//	runner.Main(runner.Registry{"user": two_sum.CsTargets, "ref/hash-map": hash_map.CsTargets}, nil, nil)
//
// Exit codes: 0 once `bye` is written; 2 for a request that cannot be run; 3 after
// `restart_requested`.
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
)

// Main runs the request named on the command line and exits. A class kind's packages also
// offer thunks, the typed method callers of their generated thunk file.
func Main(registry Registry, unavailable Unavailable, thunks Thunks) {
	keepCrashOutput()
	os.Exit(run(&loader{registry: registry, unavailable: unavailable, thunks: thunks}, os.Args[1:], os.Stderr))
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
	if req.Mode == modeBench {
		runBenchJobs(l, req.Jobs, events)
	} else if !runTestJobs(l, req.Jobs, events) {
		return exitRestart
	}
	events.bye()
	return exitCompleted
}
