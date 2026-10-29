package runner

import (
	"encoding/json"
	"fmt"
	"os"
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
)

type request struct {
	Protocol int    `json:"protocol"`
	Mode     string `json:"mode"`
	Jobs     []job  `json:"jobs"`
}

// job is a test job (target, names, cases) or a bench job (targets, inputs, settings).
type job struct {
	JobID     string        `json:"job_id"`
	Kind      string        `json:"kind"`
	Target    targetRef     `json:"target"`
	Names     names         `json:"names"`
	Signature signature     `json:"signature"`
	Cases     []testCase    `json:"cases"`
	Targets   []benchTarget `json:"targets"`
	Inputs    []benchInput  `json:"inputs"`
	Settings  benchSettings `json:"settings"`
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
	}
	return &req, nil
}

func checkJob(j *job, mode string) error {
	switch j.Kind {
	case kindFunction:
		if j.Signature.Function == nil {
			return fmt.Errorf("a function job needs signature.function")
		}
	case kindDesign, kindProgressive:
		if j.Signature.Class == nil {
			return fmt.Errorf("a class job needs signature.class")
		}
	case kindConcurrent:
		return fmt.Errorf("the go runner does not run concurrent jobs yet")
	default:
		return fmt.Errorf("unknown kind %q", j.Kind)
	}
	if mode == modeBench && len(j.Targets) == 0 {
		return fmt.Errorf("a bench job needs targets")
	}
	return nil
}

// isClass reports whether the job is one of the class kinds (an operation sequence per case).
func (j *job) isClass() bool { return j.Signature.Class != nil }
