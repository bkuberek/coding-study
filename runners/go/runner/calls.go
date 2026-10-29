package runner

import (
	"encoding/json"
	"fmt"
	"reflect"
	"slices"
	"strings"
)

// nullIndex is how `as: index` encodes a nil result.
const nullIndex = -1

// boundCall is one call's decoded arguments. Modifiers (docs/specs/problem-format.md#modifiers)
// resolve against the arguments as decoded, before the call: `ref_of` picks a node of another
// parameter, and `as: index` and `no_alias_with` compare the result with the nodes a parameter
// held, even if the call relinked them.
type boundCall struct {
	member      *checkedMember
	args        []reflect.Value
	byName      map[string]reflect.Value
	nodesBefore map[string][]any
}

// bind decodes a call's arguments from input values keyed by canonical parameter name.
func bind(m *checkedMember, values map[string]json.RawMessage) (*boundCall, error) {
	var missing []string
	for _, p := range m.params {
		if _, ok := values[p.name]; !ok {
			missing = append(missing, p.name)
		}
	}
	if len(missing) > 0 {
		return nil, &inputError{"missing input " + strings.Join(missing, ", ")}
	}
	call := &boundCall{member: m, byName: map[string]reflect.Value{}, nodesBefore: map[string][]any{}}
	parsed := map[string]any{}
	for _, p := range m.params {
		value, err := parseJSON(values[p.name])
		if err != nil {
			return nil, fmt.Errorf("%s: %w", p.name, err)
		}
		parsed[p.name] = value
		if p.refOf != "" {
			continue
		}
		decoded, err := decode(value, p.typ)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", p.name, err)
		}
		call.byName[p.name] = decoded
	}
	for _, name := range m.parametersNeedingNodes() {
		call.nodesBefore[name] = nodesIn(call.byName[name])
	}
	for _, p := range m.params {
		if p.refOf != "" {
			node, err := nodeWithValue(parsed[p.name], p, call.nodesBefore[p.refOf])
			if err != nil {
				return nil, err
			}
			call.byName[p.name] = node
		}
	}
	for _, p := range m.params {
		call.args = append(call.args, call.byName[p.name])
	}
	return call, nil
}

// bindPositional decodes an operation's arguments, given in declared order.
func bindPositional(m *checkedMember, args []json.RawMessage) (*boundCall, error) {
	if len(args) != len(m.params) {
		return nil, &inputError{fmt.Sprintf("%q takes %d arguments, the case gives %d", m.name, len(m.params), len(args))}
	}
	values := make(map[string]json.RawMessage, len(args))
	for i, p := range m.params {
		values[p.name] = args[i]
	}
	return bind(m, values)
}

func (m *checkedMember) parametersNeedingNodes() []string {
	var named []string
	add := func(name string) {
		if name != "" && !slices.Contains(named, name) {
			named = append(named, name)
		}
	}
	add(m.modifiers.Of)
	add(m.modifiers.NoAliasWith)
	for _, p := range m.params {
		add(p.refOf)
	}
	return named
}

// nodesIn lists every node reachable from a node value, or from each node of a slice of nodes.
func nodesIn(value reflect.Value) []any {
	if !value.IsValid() {
		return nil
	}
	if value.Kind() == reflect.Slice {
		var nodes []any
		for i := 0; i < value.Len(); i++ {
			nodes = append(nodes, nodesIn(value.Index(i))...)
		}
		return nodes
	}
	return traverse(value.Interface())
}

// nodeWithValue is the first node of the referenced parameter whose val equals the JSON value.
func nodeWithValue(value any, p checkedParam, candidates []any) (reflect.Value, error) {
	goType := p.typ.goType()
	if value == nil {
		return reflect.Zero(goType), nil
	}
	val, err := nodeInput(value)
	if err != nil {
		return reflect.Value{}, fmt.Errorf("%s: %w", p.name, err)
	}
	for _, node := range candidates {
		if nodeValue(node) == val {
			return reflect.ValueOf(node), nil
		}
	}
	return reflect.Value{}, &inputError{fmt.Sprintf("no node with value %d in %q", val, p.refOf)}
}

// encodeResult serializes what the call returned, applying the return modifiers.
func (c *boundCall) encodeResult(results []reflect.Value) (any, error) {
	modifiers := c.member.modifiers
	if modifiers.OutputFrom != "" {
		p := c.member.param(modifiers.OutputFrom)
		return encode(c.byName[p.name], p.typ, "")
	}
	if c.member.returns.kind == kindVoid {
		return nil, nil
	}
	result := results[0]
	switch modifiers.As {
	case "value":
		if result.IsNil() {
			return nil, nil
		}
		return nodeValue(result.Interface()), nil
	case "index":
		return c.indexIn(result, modifiers.Of)
	}
	encoded, err := encode(result, c.member.returns, "")
	if err != nil || modifiers.NoAliasWith == "" {
		return encoded, err
	}
	return encoded, c.checkNoAlias(result, modifiers.NoAliasWith)
}

func (c *boundCall) indexIn(result reflect.Value, parameter string) (any, error) {
	if result.IsNil() {
		return nullIndex, nil
	}
	node := result.Interface()
	for index, candidate := range c.nodesBefore[parameter] {
		if candidate == node {
			return index, nil
		}
	}
	return nil, &invalidOutput{fmt.Sprintf("the returned node is not a node of %q", parameter)}
}

func (c *boundCall) checkNoAlias(result reflect.Value, parameter string) error {
	inputs := map[any]bool{}
	for _, node := range c.nodesBefore[parameter] {
		inputs[node] = true
	}
	for _, node := range nodesIn(result) {
		if inputs[node] {
			return &invalidOutput{fmt.Sprintf("the returned structure shares nodes with %q", parameter)}
		}
	}
	return nil
}

func (m *checkedMember) param(name string) checkedParam {
	for _, p := range m.params {
		if p.name == name {
			return p
		}
	}
	return checkedParam{name: name}
}
