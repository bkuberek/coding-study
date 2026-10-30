package runner

import (
	"encoding/json"
	"reflect"
	"strings"
	"testing"

	"cstudy/runner/internal/fixture"
)

// counted wraps every thunk of offered so a test can tell which calls went through one.
func counted(offered TargetThunks, calls *int) TargetThunks {
	wrapped := TargetThunks{Receiver: offered.Receiver, Methods: map[string]Thunk{}}
	for name, thunk := range offered.Methods {
		wrapped.Methods[name] = func(receiver any, args []any) any {
			*calls++
			return thunk(receiver, args)
		}
	}
	return wrapped
}

// thunked is a loader whose "user" target offers the fixture's thunks of one class.
func thunked(offered TargetThunks, calls *int) *loader {
	return &loader{registry: registry, thunks: Thunks{"user": counted(offered, calls)}}
}

var (
	counterThunks = TargetThunks(fixture.CounterThunks)
	shelfThunks   = TargetThunks(fixture.ShelfThunks)
)

const shelfJob = `{"job_id": "j", "kind": "design", "target": {"compiled": "user"},
	"names": {"class": "Shelf", "constructor": "NewShelf", "methods": {"total": "Total", "later": "Later",
		"skip": "Skip", "sort": "Sort", "locate": "Locate"}},
	"signature": {"class": {"name": "Shelf", "constructor": {"params": []}, "methods": [
		{"name": "total", "params": [{"name": "values", "type": "int[]"}], "returns": {"type": "int"}},
		{"name": "later", "params": [{"name": "day", "type": "date"}, {"name": "days", "type": "decimal"}], "returns": {"type": "date"}},
		{"name": "skip", "params": [{"name": "head", "type": "ListNode"}], "returns": {"type": "ListNode"}},
		{"name": "sort", "params": [{"name": "values", "type": "int[]"}], "returns": {"type": "void", "output_from": "values"}},
		{"name": "locate", "params": [{"name": "head", "type": "ListNode"}, {"name": "node", "type": "ListNode", "ref_of": "head"}],
			"returns": {"type": "ListNode", "as": "index", "of": "head"}}]}},
	"cases": [
		{"id": "values", "ops": ["Shelf", "total", "sort", "total"], "args": [[], [[4, 1, 3]], [[4, 1, 3]], [[]]]},
		{"id": "date", "ops": ["Shelf", "later"], "args": [[], ["2024-01-30", "2"]]},
		{"id": "nodes", "ops": ["Shelf", "skip", "skip", "locate"], "args": [[], [[1, 2]], [[5]], [[5, 6, 7], 6]]},
		{"id": "bad input", "ops": ["Shelf", "total", "total"], "args": [[], [[1]], [["x"]]]},
		{"id": "nil head", "ops": ["Shelf", "skip"], "args": [[], [[]]]}]}`

// mistypedJob loads Shelf for its Mistyped method, which takes an int64 where the signature
// declares an int.
const mistypedJob = `{"job_id": "j", "kind": "design", "target": {"compiled": "user"},
	"names": {"class": "Shelf", "constructor": "NewShelf", "methods": {"mistyped": "Mistyped"}},
	"signature": {"class": {"name": "Shelf", "constructor": {"params": []}, "methods": [
		{"name": "mistyped", "params": [{"name": "value", "type": "int"}], "returns": {"type": "int"}}]}},
	"cases": [{"id": "c", "ops": ["Shelf", "mistyped"], "args": [[], [1]]}]}`

// results are the case_result events without the clock, which differs between any two runs.
func results(t *testing.T, l *loader, job string) []event {
	t.Helper()
	code, events := runRequest(t, l, testRequest(job))
	if code != exitCompleted {
		t.Fatalf("exit %d", code)
	}
	found := named(events, "case_result")
	for _, e := range found {
		delete(e, "duration_ns")
	}
	return found
}

func TestThunksGiveTheResultsOfReflection(t *testing.T) {
	tests := []struct {
		name   string
		job    string
		thunks TargetThunks
	}{
		{"counter", counterJob, counterThunks},
		{"shelf", shelfJob, shelfThunks},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			var calls int
			want := results(t, &loader{registry: registry}, tt.job)
			got := results(t, thunked(tt.thunks, &calls), tt.job)
			if !reflect.DeepEqual(got, want) {
				t.Errorf("with thunks %v\nwithout   %v", got, want)
			}
			if calls == 0 {
				t.Error("no call went through a thunk")
			}
		})
	}
}

func TestResultsOfThunksAreWhatTheCasesExpect(t *testing.T) {
	var calls int
	got := results(t, thunked(shelfThunks, &calls), shelfJob)
	wantOutputs := map[string]string{
		"values":    "[null,8,[1,3,4],0]",
		"date":      `[null,"2024-02-01"]`,
		"nodes":     "[null,[2],[],1]",
		"nil head":  "[null,[]]",
		"bad input": "",
	}
	for _, result := range got {
		id := result["case_id"].(string)
		if want := wantOutputs[id]; want != "" && asJSON(result["output"]) != want {
			t.Errorf("%s: output %s, want %s", id, asJSON(result["output"]), want)
		}
	}
}

func TestAPanicThroughAThunkNamesTheUsersFramesOnly(t *testing.T) {
	var calls int
	got := results(t, thunked(counterThunks, &calls), counterJob)
	trace := got[1]["error"].(map[string]any)["trace"].(string)
	if strings.Contains(trace, "zz_cs_thunks.go") || strings.Contains(trace, "\n") || !strings.HasSuffix(trace, " in Counter.Fail") {
		t.Errorf("trace %q", trace)
	}
}

func TestThunksOfAnotherTypeAreNotUsed(t *testing.T) {
	var calls int
	want := results(t, &loader{registry: registry}, shelfJob)
	got := results(t, thunked(counterThunks, &calls), shelfJob)
	if !reflect.DeepEqual(got, want) || calls != 0 {
		t.Errorf("%d thunk calls; got %v, want %v", calls, got, want)
	}
}

func TestAMethodWithoutAThunkIsCalledThroughReflection(t *testing.T) {
	var calls int
	partial := TargetThunks{Receiver: shelfThunks.Receiver, Methods: map[string]Thunk{"Total": shelfThunks.Methods["Total"]}}
	want := results(t, &loader{registry: registry}, shelfJob)
	got := results(t, thunked(partial, &calls), shelfJob)
	if !reflect.DeepEqual(got, want) {
		t.Errorf("got %v, want %v", got, want)
	}
	if calls != 3 {
		t.Errorf("%d thunk calls, want the 3 calls of total that decode", calls)
	}
}

func TestASignatureMismatchIsReportedWhateverThunksExist(t *testing.T) {
	var calls int
	for _, l := range []*loader{{registry: registry}, thunked(shelfThunks, &calls)} {
		_, events := runRequest(t, l, testRequest(mistypedJob))
		loadErrors := named(events, "load_error")
		if len(loadErrors) != 1 || len(named(events, "case_start")) != 0 {
			t.Fatalf("got %v", events)
		}
		failure := loadErrors[0]["error"].(map[string]any)
		if failure["type"] != "SignatureMismatch" || failure["message"] != `"Mistyped" takes int64 for "value"; int is int in Go` {
			t.Errorf("got %v", failure)
		}
	}
	if calls != 0 {
		t.Errorf("%d thunk calls", calls)
	}
}

func bindCounter(t *testing.T, l *loader) *classTarget {
	t.Helper()
	var j job
	if err := json.Unmarshal([]byte(counterJob), &j); err != nil {
		t.Fatal(err)
	}
	target, failure := l.bindClass(j.Target, j.Names, &j.Signature)
	if failure != nil {
		t.Fatalf("%v", failure)
	}
	return target
}

const incrementOps = 50

func incrementSequence() *callInput {
	ops := []string{"Counter"}
	args := [][]json.RawMessage{{}}
	for range incrementOps {
		ops = append(ops, "increment")
		args = append(args, []json.RawMessage{})
	}
	return &callInput{Ops: ops, Args: args}
}

func TestAPreparedSequenceCallsThunksWithTheDecodedArguments(t *testing.T) {
	var calls int
	call, err := bindCounter(t, thunked(counterThunks, &calls)).prepare(incrementSequence())
	if err != nil {
		t.Fatal(err)
	}
	results := call().([]any)
	if calls != incrementOps || results[incrementOps] != incrementOps {
		t.Errorf("%d thunk calls, last result %v", calls, results[incrementOps])
	}
}

func TestAPreparedSequenceWithoutThunksCallsThroughReflection(t *testing.T) {
	call, err := bindCounter(t, &loader{registry: registry}).prepare(incrementSequence())
	if err != nil {
		t.Fatal(err)
	}
	results := call().([]any)
	if last := results[incrementOps].([]reflect.Value); last[0].Int() != incrementOps {
		t.Errorf("last result %v", last)
	}
}

const counterBenchTarget = `{"target_id": "user", "target": {"compiled": "user"}, "output": true,
	"names": {"class": "Counter", "constructor": "NewCounter", "methods": {"increment": "Increment", "fail": "Fail"}}}`

const counterSignature = `{"class": {"name": "Counter", "constructor": {"params": []}, "methods": [
	{"name": "increment", "params": [], "returns": {"type": "int"}},
	{"name": "fail", "params": [], "returns": {"type": "void"}}]}}`

func TestBenchCallsTheThunksOfAClass(t *testing.T) {
	ops := `"Counter"` + strings.Repeat(`, "increment"`, incrementOps)
	args := `[]` + strings.Repeat(`, []`, incrementOps)
	body := `{"protocol": 1, "mode": "bench", "jobs": [{"job_id": "j", "kind": "design", "signature": ` + counterSignature + `,
		"targets": [` + counterBenchTarget + `],
		"inputs": [{"size": 50, "ops": [` + ops + `], "args": [` + args + `], "max_batch": 100}],
		"settings": {"reps": 3, "warmup": {"min": 1, "max": 3, "cv": 0.05}, "budget_ms": 2000, "memory": true, "min_sample_ns": 1000}}]}`
	var calls int
	code, events := runRequest(t, thunked(counterThunks, &calls), body)
	if code != exitCompleted {
		t.Fatalf("exit %d", code)
	}
	if len(named(events, "bench_sample")) != 3 || len(named(events, "bench_error")) != 0 {
		t.Errorf("events %v", events)
	}
	if outputs := named(events, "bench_output"); len(outputs) != 1 || !strings.HasSuffix(asJSON(outputs[0]["output"]), ",49,50]") {
		t.Errorf("outputs %v", outputs)
	}
	if calls < 3*incrementOps {
		t.Errorf("%d thunk calls", calls)
	}
}

// BenchmarkPreparedSequence is the cost of one operation of a prepared sequence, the part of a
// bench sample that is not the solution's own work.
func BenchmarkPreparedSequence(b *testing.B) {
	tests := []struct {
		name string
		l    *loader
	}{
		{"reflection", &loader{registry: registry}},
		{"thunks", &loader{registry: registry, thunks: Thunks{"user": counterThunks}}},
	}
	for _, tt := range tests {
		b.Run(tt.name, func(b *testing.B) {
			var j job
			if err := json.Unmarshal([]byte(counterJob), &j); err != nil {
				b.Fatal(err)
			}
			target, failure := tt.l.bindClass(j.Target, j.Names, &j.Signature)
			if failure != nil {
				b.Fatalf("%v", failure)
			}
			call, err := target.prepare(incrementSequence())
			if err != nil {
				b.Fatal(err)
			}
			b.ReportAllocs()
			b.ResetTimer()
			for range b.N {
				call()
			}
			b.ReportMetric(float64(b.Elapsed().Nanoseconds())/float64(b.N*incrementOps), "ns/op-call")
		})
	}
}
