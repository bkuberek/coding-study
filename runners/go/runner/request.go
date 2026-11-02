package runner

import (
	"encoding/json"
	"fmt"
	"os"
	"slices"
)

// protocolVersion is the runner protocol this runner speaks (docs/specs/runners.md#request-file).
const protocolVersion = 1

const (
	modeTest  = "test"
	modeBench = "bench"
)

const (
	kindFunction    = "function"
	kindDesign      = "design"
	kindProgressive = "progressive"
	kindConcurrent  = "concurrent"
	// kindProject grades a project folder compiled into the binary, as a class job
	// (docs/specs/runners.md#go-project-jobs).
	kindProject = "project"
	// kindSuite runs a project folder's native tests with `go test`.
	kindSuite = "suite"
)

// frameworkGoTest is the only framework of a Go suite job.
const frameworkGoTest = "go-test"

// modelThreads is the only concurrency model Go runs (docs/specs/problem-format.md#models-and-
// language-support).
const modelThreads = "threads"

type request struct {
	Protocol int    `json:"protocol"`
	Mode     string `json:"mode"`
	Jobs     []job  `json:"jobs"`
}

// job is a test job (target, names, cases), a bench job (targets, inputs, settings) or a suite
// job (framework, root, exclude, select, skip).
type job struct {
	JobID string `json:"job_id"`
	Kind  string `json:"kind"`
	Model string `json:"model"`
	// Clock is "virtual" for a project job on the virtual clock (clock.go).
	Clock     string        `json:"clock"`
	Target    targetRef     `json:"target"`
	Names     names         `json:"names"`
	Signature signature     `json:"signature"`
	Cases     []testCase    `json:"cases"`
	Targets   []benchTarget `json:"targets"`
	Inputs    []benchInput  `json:"inputs"`
	Settings  benchSettings `json:"settings"`
	Framework string        `json:"framework"`
	Root      string        `json:"root"`
	Exclude   []string      `json:"exclude"`
	Select    []string      `json:"select"`
	Skip      []string      `json:"skip"`
}

// targetRef names code compiled into this binary: "user" or "ref/<approach>". Compiled code has
// no path or class to load, so Go and Rust use {"compiled": "<id>"}.
type targetRef struct {
	Compiled string `json:"compiled"`
}

// names are the Go symbols the CLI computed from the naming rules; the runner converts nothing.
// Go adds "constructor" (NewLRUCache) because a Go type has no constructor syntax.
type names struct {
	Function    string            `json:"function"`
	Constructor string            `json:"constructor"`
	Methods     map[string]string `json:"methods"`
}

type signature struct {
	Function *member   `json:"function"`
	Class    *classSig `json:"class"`
}

type classSig struct {
	Name        string   `json:"name"`
	Constructor member   `json:"constructor"`
	Methods     []member `json:"methods"`
}

type member struct {
	Name    string  `json:"name"`
	Params  []param `json:"params"`
	Returns returns `json:"returns"`
	// Async marks a method that returns an awaitable, which Go methods never do.
	Async bool `json:"async"`
}

type param struct {
	Name  string `json:"name"`
	Type  string `json:"type"`
	RefOf string `json:"ref_of"`
}

// returns carries the return type and its modifiers (docs/specs/problem-format.md#modifiers).
type returns struct {
	Type        string `json:"type"`
	OutputFrom  string `json:"output_from"`
	As          string `json:"as"`
	Of          string `json:"of"`
	NoAliasWith string `json:"no_alias_with"`
}

// callInput is what one case or bench input passes: function arguments by canonical parameter
// name, or an operation sequence for class kinds.
type callInput struct {
	Input map[string]json.RawMessage `json:"input"`
	Ops   []string                   `json:"ops"`
	Args  [][]json.RawMessage        `json:"args"`
}

type testCase struct {
	ID string `json:"id"`
	callInput
	// Stress is set on the stress runs of a concurrent job, which the CLI expanded into literal
	// worker scripts (docs/specs/runners.md#concurrent-jobs).
	Stress *stressCase `json:"stress"`
}

type stressCase struct {
	Seed       int64        `json:"seed"`
	DeadlineMS int64        `json:"deadline_ms"`
	Perturb    perturbation `json:"perturb"`
	Setup      script       `json:"setup"`
	Workers    []script     `json:"workers"`
	Final      *script      `json:"final"`
}

type perturbation struct {
	YieldProbability float64 `json:"yield_probability"`
	MaxYields        int     `json:"max_yields"`
}

// script is a sequence of operations: the setup (constructor first), one worker, or the final.
type script struct {
	Ops  []string            `json:"ops"`
	Args [][]json.RawMessage `json:"args"`
}

type benchTarget struct {
	TargetID string    `json:"target_id"`
	Target   targetRef `json:"target"`
	Names    names     `json:"names"`
	Output   bool      `json:"output"`
}

type benchInput struct {
	Size int `json:"size"`
	callInput
	MaxBatch int `json:"max_batch"`
}

type benchSettings struct {
	Reps        int    `json:"reps"`
	Warmup      warmup `json:"warmup"`
	BudgetMS    int64  `json:"budget_ms"`
	Memory      bool   `json:"memory"`
	MinSampleNS int64  `json:"min_sample_ns"`
}

type warmup struct {
	Min int     `json:"min"`
	Max int     `json:"max"`
	CV  float64 `json:"cv"`
}

// readRequest parses and checks the request file; any error makes it a bad request (exit 2),
// reported before a case starts.
func readRequest(path string) (*request, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var req request
	if err := json.Unmarshal(data, &req); err != nil {
		return nil, err
	}
	if req.Protocol != protocolVersion {
		return nil, fmt.Errorf("unknown protocol %d", req.Protocol)
	}
	if req.Mode != modeTest && req.Mode != modeBench {
		return nil, fmt.Errorf("unknown mode %q", req.Mode)
	}
	for i := range req.Jobs {
		if err := checkJob(&req.Jobs[i], req.Mode); err != nil {
			return nil, fmt.Errorf("job %q: %w", req.Jobs[i].JobID, err)
		}
		if req.Jobs[i].Kind == kindSuite && len(req.Jobs) > 1 {
			return nil, fmt.Errorf("job %q: a suite job comes alone", req.Jobs[i].JobID)
		}
	}
	return &req, nil
}

func checkJob(j *job, mode string) error {
	switch j.Kind {
	case kindFunction:
		if j.Signature.Function == nil {
			return fmt.Errorf("a function job needs signature.function")
		}
	case kindSuite:
		return checkSuite(j, mode)
	case kindDesign, kindProgressive, kindProject:
		if j.Signature.Class == nil {
			return fmt.Errorf("a class job needs signature.class")
		}
	case kindConcurrent:
		if err := checkConcurrent(j, mode); err != nil {
			return err
		}
	default:
		return fmt.Errorf("unknown kind %q", j.Kind)
	}
	if err := checkStressCases(j); err != nil {
		return err
	}
	if err := checkClock(j); err != nil {
		return err
	}
	if mode == modeBench && len(j.Targets) == 0 {
		return fmt.Errorf("a bench job needs targets")
	}
	return nil
}

func checkSuite(j *job, mode string) error {
	switch {
	case mode != modeTest:
		return fmt.Errorf("a suite job runs in test mode")
	case j.Framework != frameworkGoTest:
		return fmt.Errorf("the go runner runs %q suites, not %q", frameworkGoTest, j.Framework)
	case j.Root == "":
		return fmt.Errorf("a suite job needs its root")
	}
	return nil
}

// checkStressCases allows stress cases in concurrent jobs and in a project's grading job, which
// runs them as a concurrent job does, in the threads model
// (docs/specs/runners.md#stress-in-project-jobs).
func checkStressCases(j *job) error {
	if !slices.ContainsFunc(j.Cases, isStress) {
		return nil
	}
	switch {
	case j.Kind == kindProject && j.Model != modelThreads:
		return fmt.Errorf("a project's stress cases run the threads model, not %q", j.Model)
	case j.Kind == kindProject:
		return checkStressSetups(j)
	case j.Kind != kindConcurrent:
		return fmt.Errorf("only a concurrent or project job has stress cases")
	}
	return nil
}

func checkConcurrent(j *job, mode string) error {
	switch {
	case j.Model != modelThreads:
		return fmt.Errorf("the go runner runs the threads model only, not %q", j.Model)
	case mode == modeBench:
		return fmt.Errorf("concurrent problems have no bench")
	case j.Signature.Class == nil:
		return fmt.Errorf("a concurrent job needs signature.class")
	}
	return checkStressSetups(j)
}

func checkStressSetups(j *job) error {
	for _, c := range j.Cases {
		if c.Stress != nil && len(c.Stress.Setup.Ops) == 0 {
			return fmt.Errorf("stress case %q has no constructor in its setup", c.ID)
		}
	}
	return nil
}

// checkClock allows the virtual clock in project jobs only, and refuses asynchronous methods:
// a Go method that waits blocks its goroutine instead of returning an awaitable.
func checkClock(j *job) error {
	switch {
	case j.Clock != "" && j.Clock != clockVirtual:
		return fmt.Errorf("unknown clock %q", j.Clock)
	case j.Clock != "" && j.Kind != kindProject:
		return fmt.Errorf("only a project job runs on the virtual clock")
	case j.Signature.Class != nil && slices.ContainsFunc(j.Signature.Class.Methods, isAsync):
		return fmt.Errorf("a Go method cannot be async: it blocks its goroutine")
	}
	return nil
}

func isStress(c testCase) bool { return c.Stress != nil }

func isAsync(m member) bool { return m.Async }

// isClass reports whether the job is one of the class kinds (an operation sequence per case).
func (j *job) isClass() bool { return j.Signature.Class != nil }
