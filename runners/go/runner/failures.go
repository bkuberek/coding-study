package runner

import (
	"bytes"
	"fmt"
	"path/filepath"
	"reflect"
	"runtime"
	"slices"
	"strings"
	"time"
)

const (
	maxTraceLines = 10
	// panicType is the error type of a panic with a value that is not an error, such as the
	// stubs' panic("not implemented").
	panicType = "panic"
	// thunkFile is the generated file of a class's method thunks; its frames are not the user's.
	thunkFile = "zz_cs_thunks.go"
)

// userError is the `error` object of an event.
type userError struct {
	Type    string
	Message string
	Trace   string
}

// MarshalJSON keeps type, message, trace in that order and omits an empty trace.
func (e *userError) MarshalJSON() ([]byte, error) {
	var out bytes.Buffer
	out.WriteString(`{"type":`)
	out.Write(marshal(e.Type))
	out.WriteString(`,"message":`)
	out.Write(marshal(e.Message))
	if e.Trace != "" {
		out.WriteString(`,"trace":`)
		out.Write(marshal(e.Trace))
	}
	out.WriteByte('}')
	return out.Bytes(), nil
}

func inputFailure(err error) *userError {
	return &userError{Type: "InvalidInput", Message: err.Error()}
}

// timedCall is what one call into user code did: its results, or the panic it raised.
type timedCall struct {
	results    []reflect.Value
	failure    *userError
	durationNS int64
}

// invoke calls user code and recovers a panic as a userError whose trace keeps only frames of
// pkg; durationNS covers the call only.
func invoke(fn reflect.Value, args []reflect.Value, pkg string) timedCall {
	return timeCall(pkg, func() []reflect.Value { return fn.Call(args) })
}

// invokeThunk is invoke for a method called through its generated thunk. The arguments are
// converted before the clock starts, the result after it stops.
func invokeThunk(thunk Thunk, receiver any, args []reflect.Value, pkg string) timedCall {
	arguments := anyArguments(args)
	var result any
	call := timeCall(pkg, func() []reflect.Value {
		result = thunk(receiver, arguments)
		return nil
	})
	if call.failure == nil && result != nil {
		call.results = []reflect.Value{reflect.ValueOf(result)}
	}
	return call
}

func timeCall(pkg string, call func() []reflect.Value) (timed timedCall) {
	start := time.Now()
	defer func() {
		timed.durationNS = time.Since(start).Nanoseconds()
		if recovered := recover(); recovered != nil {
			timed.failure = describePanic(recovered, pkg)
		}
	}()
	return timedCall{results: call()}
}

// anyArguments are the decoded arguments as the any values that a thunk asserts.
func anyArguments(args []reflect.Value) []any {
	arguments := make([]any, len(args))
	for i, arg := range args {
		arguments[i] = arg.Interface()
	}
	return arguments
}

// describePanic runs inside the deferred recover, while the panicking frames are still on the
// goroutine's stack, so runtime.Callers sees the user line that panicked.
func describePanic(recovered any, pkg string) *userError {
	errorType := panicType
	if err, ok := recovered.(error); ok {
		errorType = fmt.Sprintf("%T", err)
	}
	return &userError{Type: errorType, Message: fmt.Sprint(recovered), Trace: userTrace(pkg)}
}

// userTrace lists the frames of pkg on the current stack, innermost last like the other
// runners, at most maxTraceLines: `two_sum.go:7 in twoSum`, `lru_cache.go:31 in LRUCache.Get`.
func userTrace(pkg string) string {
	pcs := make([]uintptr, 256)
	frames := runtime.CallersFrames(pcs[:runtime.Callers(0, pcs)])
	var lines []string
	for {
		frame, more := frames.Next()
		function, ok := strings.CutPrefix(frame.Function, pkg)
		if ok && filepath.Base(frame.File) != thunkFile {
			lines = append(lines, fmt.Sprintf("%s:%d in %s", filepath.Base(frame.File), frame.Line, readableFunction(function)))
		}
		if !more {
			break
		}
	}
	slices.Reverse(lines)
	if len(lines) > maxTraceLines {
		lines = lines[len(lines)-maxTraceLines:]
	}
	return strings.Join(lines, "\n")
}

// readableFunction turns a method's symbol `(*LRUCache).Get` into `LRUCache.Get`.
func readableFunction(function string) string {
	return strings.NewReplacer("(*", "", ")", "").Replace(function)
}

// packageOf is the import path prefix of fn's package ("workspace/practice/two_sum."), which
// marks the frames of user code in traces.
func packageOf(fn reflect.Value) string {
	name := runtime.FuncForPC(fn.Pointer()).Name()
	slash := strings.LastIndex(name, "/")
	dot := strings.Index(name[slash+1:], ".")
	if dot < 0 {
		return name
	}
	return name[:slash+1+dot+1]
}
