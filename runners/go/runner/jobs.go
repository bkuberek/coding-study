package runner

import (
	"encoding/json"
	"fmt"
	"reflect"
)

// constructorOp is the index of the constructor in an operation sequence.
const constructorOp = 0

// runTestJobs runs the cases of each job (docs/specs/runners.md#event-stream). Inputs are
// decoded fresh for every case; duration_ns covers only the calls into user code.
func runTestJobs(l *loader, jobs []job, events *writer) {
	for i := range jobs {
		j := &jobs[i]
		events.jobStart(j.JobID)
		target, failure := l.bind(j.Target, j.Names, &j.Signature)
		if failure != nil {
			events.loadError(j.JobID, failure)
		} else {
			for k := range j.Cases {
				c := &j.Cases[k]
				events.caseStart(j.JobID, c.ID)
				events.caseResult(j.JobID, c.ID, target.run(&c.callInput))
			}
		}
		events.jobEnd(j.JobID)
	}
}

func (t *functionTarget) run(input *callInput) outcome {
	if input.Input == nil {
		return raised(inputFailure(fmt.Errorf("a function job takes arguments, not an operation sequence")), 0)
	}
	call, err := bind(t.call, input.Input)
	if err != nil {
		return raised(inputFailure(err), 0)
	}
	output := startCapture()
	timed := invoke(t.fn, call.args, t.pkg)
	stdout := output.stop()
	result := t.encode(call, timed)
	result.stdout = stdout
	return result
}

func (t *functionTarget) encode(call *boundCall, timed timedCall) outcome {
	if timed.failure != nil {
		return raised(timed.failure, timed.durationNS)
	}
	encoded, err := call.encodeResult(timed.results)
	if err != nil {
		return invalid(err.Error(), timed.durationNS)
	}
	return returned(encoded, timed.durationNS)
}

func (t *functionTarget) prepare(input *callInput) (func() any, error) {
	if input.Input == nil {
		return nil, fmt.Errorf("a function job takes arguments, not an operation sequence")
	}
	call, err := bind(t.call, input.Input)
	if err != nil {
		return nil, err
	}
	return func() any { return t.fn.Call(call.args) }, nil
}

// operations is one case of a class kind: the constructor, then each operation on the new
// instance.
type operations struct {
	target   *classTarget
	instance reflect.Value
	outputs  []any
	duration int64
}

func (t *classTarget) run(input *callInput) outcome {
	output := startCapture()
	result := (&operations{target: t, outputs: []any{}}).run(input)
	result.stdout = output.stop()
	return result
}

func (o *operations) run(input *callInput) outcome {
	if len(input.Ops) != len(input.Args) {
		return o.failed(constructorOp, fmt.Errorf("%d operations but %d argument lists", len(input.Ops), len(input.Args)))
	}
	if len(input.Ops) == 0 {
		return o.failed(constructorOp, fmt.Errorf("a class job takes an operation sequence, not arguments"))
	}
	for index, op := range input.Ops {
		if result, done := o.operation(index, op, input.Args[index]); done {
			return result
		}
	}
	return returned(o.outputs, o.duration)
}

// operation runs one operation; done when it ends the case.
func (o *operations) operation(index int, op string, args []json.RawMessage) (outcome, bool) {
	m, err := o.target.member(index, op)
	if err != nil {
		return o.failed(index, err), true
	}
	call, err := bindPositional(m, args)
	if err != nil {
		return o.failed(index, err), true
	}
	fn := o.target.constructor
	if index != constructorOp {
		fn = o.instance.Method(o.target.methods[op].index)
	}
	timed := invoke(fn, call.args, o.target.pkg)
	o.duration += timed.durationNS
	if timed.failure != nil {
		return o.raised(index, timed.failure), true
	}
	if index == constructorOp {
		o.instance = addressable(timed.results[0])
		o.outputs = append(o.outputs, nil)
		return outcome{}, false
	}
	encoded, err := call.encodeResult(timed.results)
	if err != nil {
		return invalid(fmt.Sprintf("operation %d (%s): %s", index, op, err), o.duration), true
	}
	o.outputs = append(o.outputs, encoded)
	return outcome{}, false
}

func (o *operations) failed(index int, err error) outcome {
	return o.raised(index, inputFailure(err))
}

func (o *operations) raised(index int, err *userError) outcome {
	result := raised(err, o.duration)
	result.opIndex = index
	result.partialOutput = append([]any{}, o.outputs...)
	return result
}

// member is the constructor at index 0 and a declared method after it.
func (t *classTarget) member(index int, op string) (*checkedMember, error) {
	if index == constructorOp {
		if op != t.className {
			return nil, fmt.Errorf("operation 0 must be %q, got %q", t.className, op)
		}
		return t.create, nil
	}
	method, ok := t.methods[op]
	if !ok {
		return nil, fmt.Errorf("unknown operation %q at index %d", op, index)
	}
	return method.call, nil
}

// addressable makes a constructor's value result a pointer, so methods with pointer receivers
// can be called on it.
func addressable(instance reflect.Value) reflect.Value {
	if instance.Kind() == reflect.Pointer {
		return instance
	}
	pointer := reflect.New(instance.Type())
	pointer.Elem().Set(instance)
	return pointer
}

// prepare decodes the whole sequence; the call constructs, then calls each method on the
// instance, and returns every result so nothing is freed inside the timed region.
func (t *classTarget) prepare(input *callInput) (func() any, error) {
	if len(input.Ops) == 0 || len(input.Ops) != len(input.Args) {
		return nil, fmt.Errorf("a class job takes an operation sequence, not arguments")
	}
	methods := make([]int, len(input.Ops))
	arguments := make([][]reflect.Value, len(input.Ops))
	for index, op := range input.Ops {
		m, err := t.member(index, op)
		if err != nil {
			return nil, err
		}
		call, err := bindPositional(m, input.Args[index])
		if err != nil {
			return nil, err
		}
		if index != constructorOp {
			methods[index] = t.methods[op].index
		}
		arguments[index] = call.args
	}
	return func() any {
		instance := addressable(t.constructor.Call(arguments[constructorOp])[0])
		results := make([]any, len(methods))
		results[constructorOp] = instance
		for index := constructorOp + 1; index < len(methods); index++ {
			results[index] = instance.Method(methods[index]).Call(arguments[index])
		}
		return results
	}, nil
}
