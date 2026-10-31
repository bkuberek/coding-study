package runner

import (
	"fmt"
	"reflect"
)

// Registry maps a compiled target id ("user", "ref/hash-map") to the symbols its generated
// registration file exposes: the function or the constructor, by Go name. Methods are not
// registered: they are found with MethodByName, which is why Go methods are exported.
type Registry map[string]map[string]any

// Thunk calls one method of a class with its arguments already of the method's Go types, and
// returns the result as an any (nil for a method without one).
type Thunk = func(receiver any, args []any) any

// TargetThunks are the typed callers that a class kind's generated thunk file offers for the
// methods of its type. Receiver is a nil *T, the type the thunks assert their receiver to be;
// Methods are keyed by Go method name. A zero value offers none.
type TargetThunks struct {
	Receiver any
	Methods  map[string]Thunk
}

// Thunks maps a compiled target id to its thunks. A method without a thunk is called through
// reflection, and so is every method of a target whose thunk file did not compile
// (docs/specs/runners.md#go-build-details).
type Thunks map[string]TargetThunks

// Unavailable maps a target id to the symbols whose registration did not compile, with the
// compiler's message; the CLI rebuilt without them, and their jobs get a load_error
// (docs/specs/runners.md#locating-user-code).
type Unavailable map[string]map[string]string

// checkedMember is a function, constructor or method whose Go signature matches the DSL.
type checkedMember struct {
	name    string
	symbol  string
	params  []checkedParam
	returns *dslType
	// modifiers are the declared return's modifiers (output_from, as, of, no_alias_with).
	modifiers returns
}

type checkedParam struct {
	name  string
	typ   *dslType
	refOf string
}

type loader struct {
	registry    Registry
	unavailable Unavailable
	thunks      Thunks
	// broken holds the targets whose code did not compile, with the compiler's error: a project
	// built without them (docs/specs/runners.md#go-project-jobs).
	broken map[string]*userError
}

// lookup finds a registered symbol of a target, or explains why it is missing.
func (l *loader) lookup(ref targetRef, symbol, what string) (reflect.Value, *userError) {
	if failure, ok := l.broken[ref.Compiled]; ok {
		return reflect.Value{}, failure
	}
	symbols, ok := l.registry[ref.Compiled]
	if !ok {
		return reflect.Value{}, &userError{Type: "LoadError",
			Message: fmt.Sprintf("target %q is not part of this build", ref.Compiled)}
	}
	if value, ok := symbols[symbol]; ok {
		return reflect.ValueOf(value), nil
	}
	message := fmt.Sprintf("the package defines no %s %q", what, symbol)
	if reason, ok := l.unavailable[ref.Compiled][symbol]; ok {
		message += ": " + reason
	}
	return reflect.Value{}, &userError{Type: "SymbolNotFound", Message: message}
}

// check fails unless fnType takes exactly the declared parameters after `skip` leading inputs
// (the receiver of a method) and returns the declared type; a constructor returns one value.
func check(symbol string, fnType reflect.Type, skip int, m member, constructor bool) (*checkedMember, *userError) {
	fail := func(format string, args ...any) (*checkedMember, *userError) {
		message := fmt.Sprintf("%q ", symbol) + fmt.Sprintf(format, args...)
		return nil, &userError{Type: "SignatureMismatch", Message: message}
	}
	if fnType.Kind() != reflect.Func {
		return fail("is not a function")
	}
	if fnType.IsVariadic() || fnType.NumIn()-skip != len(m.Params) {
		return fail("takes %d parameters; the signature declares %d", fnType.NumIn()-skip, len(m.Params))
	}
	checked := &checkedMember{name: m.Name, symbol: symbol, modifiers: m.Returns}
	for i, p := range m.Params {
		t, want, err := mapped(p.Type, parseType)
		if err != nil {
			return nil, err
		}
		if got := fnType.In(i + skip); got != want {
			return fail("takes %v for %q; %s is %v in Go", got, p.Name, p.Type, want)
		}
		checked.params = append(checked.params, checkedParam{name: p.Name, typ: t, refOf: p.RefOf})
	}
	if constructor {
		return checked, nil
	}
	ret, want, err := mapped(m.Returns.Type, parseReturn)
	if err != nil {
		return nil, err
	}
	checked.returns = ret
	if want == nil {
		if fnType.NumOut() != 0 {
			return fail("returns a value; the signature declares void")
		}
		return checked, nil
	}
	if fnType.NumOut() != 1 || fnType.Out(0) != want {
		return fail("must return %v for %s", want, m.Returns.Type)
	}
	return checked, nil
}

// mapped parses a DSL type and finds its Go type.
func mapped(text string, parse func(string) (*dslType, error)) (*dslType, reflect.Type, *userError) {
	t, err := parse(text)
	if err != nil {
		return nil, nil, &userError{Type: "SignatureMismatch", Message: err.Error()}
	}
	return t, t.goType(), nil
}

type functionTarget struct {
	fn   reflect.Value
	call *checkedMember
	pkg  string
}

func (l *loader) bindFunction(ref targetRef, n names, sig *signature) (*functionTarget, *userError) {
	value, err := l.lookup(ref, n.Function, "function")
	if err != nil {
		return nil, err
	}
	call, err := check(n.Function, value.Type(), 0, *sig.Function, false)
	if err != nil {
		return nil, err
	}
	return &functionTarget{fn: value, call: call, pkg: packageOf(value)}, nil
}

type classTarget struct {
	className   string
	constructor reflect.Value
	create      *checkedMember
	methods     map[string]*boundMethod
	pkg         string
}

type boundMethod struct {
	index int
	call  *checkedMember
	// thunk is nil when the method is called through reflection.
	thunk Thunk
}

func (l *loader) bindClass(ref targetRef, n names, sig *signature) (*classTarget, *userError) {
	declared := sig.Class
	value, err := l.lookup(ref, n.Constructor, "constructor")
	if err != nil {
		return nil, err
	}
	ctorType := value.Type()
	if ctorType.Kind() != reflect.Func || ctorType.NumOut() != 1 || ctorType.Out(0).Kind() == reflect.Interface {
		return nil, &userError{Type: "SignatureMismatch",
			Message: fmt.Sprintf("%q must return the new *%s and nothing else", n.Constructor, declared.Name)}
	}
	create, err := check(n.Constructor, ctorType, 0, declared.Constructor, true)
	if err != nil {
		return nil, err
	}
	create.name = declared.Name
	target := &classTarget{className: declared.Name, constructor: value, create: create,
		methods: map[string]*boundMethod{}, pkg: packageOf(value)}
	// Methods with pointer receivers are in the method set of *T only.
	receiver := ctorType.Out(0)
	if receiver.Kind() != reflect.Pointer {
		receiver = reflect.PointerTo(receiver)
	}
	thunks := l.thunksFor(ref, receiver)
	for _, m := range declared.Methods {
		symbol := n.Methods[m.Name]
		found, ok := receiver.MethodByName(symbol)
		if !ok {
			return nil, &userError{Type: "SymbolNotFound",
				Message: fmt.Sprintf("%v has no exported method %q", receiver, symbol)}
		}
		call, err := check(symbol, found.Type, 1, m, false)
		if err != nil {
			return nil, err
		}
		target.methods[m.Name] = &boundMethod{index: found.Index, call: call, thunk: thunks[symbol]}
	}
	return target, nil
}

// thunksFor are the thunks of a target that were generated for the type its constructor
// returns; a thunk asserts its receiver, so thunks for any other type are not used. Reflection
// still checks every signature first, so a mismatch is reported the same way with or without them.
func (l *loader) thunksFor(ref targetRef, receiver reflect.Type) map[string]Thunk {
	offered := l.thunks[ref.Compiled]
	if offered.Receiver == nil || reflect.TypeOf(offered.Receiver) != receiver {
		return nil
	}
	return offered.Methods
}

// caseRunner is a loaded target of either kind.
type caseRunner interface {
	// run executes one case as `cstudy test` does, capturing what the code prints.
	run(input *callInput) outcome
	// prepare decodes fresh arguments for one uncaptured call of the whole case (bench mode).
	prepare(input *callInput) (func() any, error)
	// userPackage marks the frames of the target's code in traces.
	userPackage() string
}

func (t *functionTarget) userPackage() string { return t.pkg }

func (t *classTarget) userPackage() string { return t.pkg }

func (l *loader) bind(ref targetRef, n names, sig *signature) (caseRunner, *userError) {
	if sig.Class != nil {
		return asRunner(l.bindClass(ref, n, sig))
	}
	return asRunner(l.bindFunction(ref, n, sig))
}

func asRunner[T caseRunner](target T, failure *userError) (caseRunner, *userError) {
	if failure != nil {
		return nil, failure
	}
	return target, nil
}
