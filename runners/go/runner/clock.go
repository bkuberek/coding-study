package runner

import (
	"encoding/json"
	"fmt"
	"os"
	"reflect"
	"strings"
	"sync"
	"time"
)

// The virtual clock of project problems (docs/specs/runners.md#virtual-clock-and-stress-in-
// project-jobs). A virtual-clock project's grading binary is a test binary (`go test -c`): its
// generated TestMain hands MainOnClock the test framework's run, and its one test hands
// GradeOnClock the bubble of testing/synctest, so this package never imports testing.
//
// Each case runs in a bubble of its own, where the time package reads a clock that moves only
// while every goroutine of the bubble is durably blocked, and the case settles after each
// operation. A case whose goroutines all wait while no timer is due deadlocks: the runtime ends
// the bubble with a panic, which is the case's `stalled`, and the goroutines stay blocked for
// good, so the runner asks for a restart.

const (
	clockVirtual = "virtual"
	opAdvance    = "@advance"
	opSpawn      = "@spawn"
	opJoin       = "@join"
	opNow        = "@now"
	// gradingTest is the test of the generated test file that runs the request.
	gradingTest = "TestCsGrading"
	// deadlockPrefix starts the message of the runtime's panic when a bubble deadlocks.
	deadlockPrefix = "deadlock: "
	clockFeature   = "clock"
)

// Clock is what the grading test of a virtual-clock test binary hands the runner.
type Clock struct {
	// Bubble runs body in a bubble of its own and returns once every goroutine of the bubble
	// has ended (synctest.Test). It panics with the runtime's deadlock error when every
	// goroutine of the bubble is durably blocked while no timer is due, and when goroutines are
	// left once body returned.
	Bubble func(body func())
	// Settle returns once every other goroutine of the bubble is durably blocked
	// (synctest.Wait).
	Settle func()
}

// clockMain is the request that MainOnClock read from the command line, for GradeOnClock: the
// test framework runs between them.
var clockMain struct {
	loader *loader
	argv   []string
}

// MainOnClock runs the request named on the command line of a virtual-clock test binary, and
// exits. It leaves the test framework only the flag that selects the grading test, then runs
// the tests (m.Run), whose grading test calls GradeOnClock.
func MainOnClock(registry Registry, unavailable Unavailable, thunks Thunks, runTests func() int) {
	keepCrashOutput()
	clockMain.loader = &loader{registry: registry, unavailable: unavailable, thunks: thunks}
	clockMain.argv = os.Args[1:]
	os.Args = []string{os.Args[0], "-test.run=^" + gradingTest + "$"}
	runTests()
	fmt.Fprintf(os.Stderr, "cs-go-runner: the test binary did not run %s\n", gradingTest)
	os.Exit(exitBadRequest)
}

// GradeOnClock is the body of the grading test: it runs the request that MainOnClock read on
// the test's clock, and exits.
func GradeOnClock(clock Clock) {
	l := clockMain.loader
	if l == nil {
		fmt.Fprintln(os.Stderr, "cs-go-runner: GradeOnClock runs only under MainOnClock")
		os.Exit(exitBadRequest)
	}
	l.clock = &clock
	os.Exit(run(l, clockMain.argv, os.Stderr))
}

// features are what this binary announces in hello. A test binary has the virtual clock, and a
// project that did not build answers every job, a virtual-clock one too, with its errors.
func (l *loader) features() []string {
	features := []string{stressFeature, projectFeature, suiteFeature, projectStressFeature}
	if l.clock != nil || l.broken != nil {
		features = append(features, clockFeature)
	}
	return features
}

// onClock reports whether the job's cases run on the virtual clock: every project job of a test
// binary does, since only a virtual-clock project is built as one.
func (l *loader) onClock(j *job) bool { return l.clock != nil && j.Kind == kindProject }

// clockFailure refuses a virtual-clock job to a binary without the clock.
func (l *loader) clockFailure(j *job) *userError {
	if j.Clock != clockVirtual || l.clock != nil {
		return nil
	}
	return &userError{Type: "LoadError",
		Message: "this runner was built without the virtual clock, which a test binary has"}
}

// runClockCase reports one case on the virtual clock, then asks for a restart when the case left
// goroutines behind: Go cannot end them, and those of a deadlock stay blocked for good.
func runClockCase(jobID string, c *testCase, target *classTarget, clock *Clock, events *writer) bool {
	run := &clockCase{clock: clock, tasks: map[string]*task{}}
	events.caseResult(jobID, c.ID, run.captured(target, &c.callInput))
	if run.leftBehind {
		events.restartRequested(fmt.Sprintf("goroutines of %s are still blocked", c.ID))
		return false
	}
	return true
}

// clockCase is one case on the virtual clock.
type clockCase struct {
	clock *Clock
	// tasks are the calls that @spawn started and no @join has waited for yet.
	tasks map[string]*task
	// leftBehind is set when the case ended with goroutines of its bubble still there.
	leftBehind bool

	// Written in the bubble, read once the bubble deadlocked: the runtime ends it with every
	// goroutine blocked, so mu is free then.
	mu       sync.Mutex
	started  time.Time
	opIndex  int
	label    string
	partial  []any
	finished bool
}

// task is a call that @spawn started; its result waits for @join.
type task struct {
	call   *boundCall
	result chan timedCall
}

// captured runs the case with what its code prints captured. The capture starts outside the
// bubble: its reader waits on a pipe, which is not a durable block, so inside the bubble it
// would keep the clock from moving. duration_ns is the real time of the whole case, since every
// clock inside the bubble is virtual.
func (c *clockCase) captured(target *classTarget, input *callInput) outcome {
	freshDecimalSettings()
	output := startCapture()
	start := time.Now()
	result := c.run(target, input)
	result.durationNS = time.Since(start).Nanoseconds()
	result.stdout = output.stop()
	return result
}

func (c *clockCase) run(target *classTarget, input *callInput) (result outcome) {
	defer func() {
		recovered := recover()
		if recovered == nil {
			return
		}
		if err, ok := recovered.(error); !ok || !strings.HasPrefix(err.Error(), deadlockPrefix) {
			panic(recovered)
		}
		result = c.deadlocked(result, recovered)
	}()
	c.clock.Bubble(func() {
		c.mu.Lock()
		c.started = time.Now()
		c.mu.Unlock()
		done := (&operations{target: target, outputs: []any{}, clock: c}).run(input)
		c.mu.Lock()
		result, c.finished = done, true
		c.mu.Unlock()
	})
	return result
}

// deadlocked is the outcome of a case whose bubble deadlocked: stalled at the operation in
// progress, or, when the case ended with goroutines left, at its last operation, unless the case
// had already failed.
func (c *clockCase) deadlocked(result outcome, deadlock any) outcome {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.leftBehind = true
	if c.finished && result.status != statusOK {
		return result
	}
	what := "deadlock"
	if c.finished {
		what = "the case ended with goroutines still blocked"
	}
	reason := fmt.Sprintf("op %d (%s): %s", c.opIndex, c.label, what)
	if now, ok := deadlockTime(deadlock); ok {
		reason += fmt.Sprintf(" at %d ms", time.Duration(now-c.started.UnixNano()).Milliseconds())
	}
	return outcome{status: statusStalled, reason: reason, opIndex: c.opIndex, partialOutput: c.partial}
}

// deadlockTime is the virtual time, in Unix nanoseconds, at which a bubble deadlocked.
// testing/synctest offers no way to read a bubble's clock once every goroutine in it is blocked
// for good, and the runtime's deadlock error carries the bubble, so its clock is read by
// reflection; false when the error does not have that shape.
func deadlockTime(deadlock any) (int64, bool) {
	value := reflect.ValueOf(deadlock)
	if value.Kind() != reflect.Struct {
		return 0, false
	}
	bubble := value.FieldByName("bubble")
	if bubble.Kind() != reflect.Pointer || bubble.IsNil() || bubble.Elem().Kind() != reflect.Struct {
		return 0, false
	}
	now := bubble.Elem().FieldByName("now")
	if now.Kind() != reflect.Int64 {
		return 0, false
	}
	return now.Int(), true
}

// step is one operation of a case on the virtual clock, a harness operation or a call as on the
// real clock, after which the case settles, so the next operation sees every goroutine of the
// bubble blocked.
func (c *clockCase) step(o *operations, index int, op string, args []json.RawMessage) (outcome, bool) {
	c.enter(index, op, args, o.outputs)
	var result outcome
	var done bool
	if index != constructorOp && strings.HasPrefix(op, harnessPrefix) {
		result, done = c.harness(o, index, op, args)
	} else {
		result, done = o.operation(index, op, args)
	}
	if !done {
		c.clock.Settle()
	}
	return result, done
}

// enter records the operation in progress, which a deadlock names.
func (c *clockCase) enter(index int, op string, args []json.RawMessage, outputs []any) {
	label := op
	if op == opSpawn || op == opJoin {
		if name, ok := stringArgument(args, 0); ok {
			label += " " + name
		}
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	c.opIndex, c.label, c.partial = index, label, append([]any{}, outputs...)
}

func (c *clockCase) harness(o *operations, index int, op string, args []json.RawMessage) (outcome, bool) {
	var output any
	var err error
	switch op {
	case opAdvance:
		err = c.advance(args)
	case opSpawn:
		err = c.spawn(o, args)
	case opJoin:
		return c.join(o, index, args)
	case opNow:
		output, err = c.now(args)
	default:
		err = fmt.Errorf("unknown harness operation %q at index %d", op, index)
	}
	if err != nil {
		return o.failed(index, err), true
	}
	o.outputs = append(o.outputs, output)
	return outcome{}, false
}

// advance is `@advance [ms]`: the clock moves ms milliseconds, firing each timer due on the way
// at its own time.
func (c *clockCase) advance(args []json.RawMessage) error {
	if len(args) != 1 {
		return fmt.Errorf("%s takes the milliseconds to move the clock", opAdvance)
	}
	var milliseconds int64
	if err := json.Unmarshal(args[0], &milliseconds); err != nil || milliseconds < 0 {
		return fmt.Errorf("%s takes a number of milliseconds of 0 or more, not %s", opAdvance, args[0])
	}
	time.Sleep(time.Duration(milliseconds) * time.Millisecond)
	return nil
}

// spawn is `@spawn [task, method, ...arguments]`: the call runs on a goroutine of its own, and
// its result waits for the @join of the task.
func (c *clockCase) spawn(o *operations, args []json.RawMessage) error {
	name, named := stringArgument(args, 0)
	method, methodNamed := stringArgument(args, 1)
	if !named || !methodNamed {
		return fmt.Errorf("%s takes a task name, a method and the method's arguments", opSpawn)
	}
	if _, running := c.tasks[name]; running {
		return fmt.Errorf("task %q was spawned and not joined yet", name)
	}
	bound, ok := o.target.methods[method]
	if !ok {
		return fmt.Errorf("%s of an unknown method %q", opSpawn, method)
	}
	call, err := bindPositional(bound.call, args[2:])
	if err != nil {
		return err
	}
	spawned := &task{call: call, result: make(chan timedCall, 1)}
	c.tasks[name] = spawned
	instance := o.instance
	go func() { spawned.result <- o.target.invokeMethod(bound, instance, call.args) }()
	return nil
}

// join is `@join [task]`: it waits for the task's call, the clock moving while every goroutine
// waits, and outputs the call's result, or fails with its panic.
func (c *clockCase) join(o *operations, index int, args []json.RawMessage) (outcome, bool) {
	name, named := stringArgument(args, 0)
	if !named || len(args) != 1 {
		return o.failed(index, fmt.Errorf("%s takes the name of a spawned task", opJoin)), true
	}
	spawned, ok := c.tasks[name]
	if !ok {
		return o.failed(index, fmt.Errorf("%s of task %q, which no @spawn started", opJoin, name)), true
	}
	delete(c.tasks, name)
	timed := <-spawned.result
	if timed.failure != nil {
		return o.raised(index, timed.failure), true
	}
	encoded, err := spawned.call.encodeResult(timed.results)
	if err != nil {
		return invalid(fmt.Sprintf("operation %d (%s %s): %s", index, opJoin, name, err), o.duration), true
	}
	o.outputs = append(o.outputs, encoded)
	return outcome{}, false
}

// now is `@now []`: the virtual milliseconds since the case started.
func (c *clockCase) now(args []json.RawMessage) (any, error) {
	if len(args) != 0 {
		return nil, fmt.Errorf("%s takes no arguments", opNow)
	}
	return time.Since(c.started).Milliseconds(), nil
}

// stringArgument is the string at args[index]; false when there is none.
func stringArgument(args []json.RawMessage, index int) (string, bool) {
	if index >= len(args) {
		return "", false
	}
	return jsonString(args[index])
}
