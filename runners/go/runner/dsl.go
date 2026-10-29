package runner

import (
	"fmt"
	"reflect"
	"strings"

	"cstudy/support"
)

type kind int

const (
	kindInt kind = iota
	kindLong
	kindDouble
	kindBool
	kindString
	kindChar
	kindDecimal
	kindDate
	kindListNode
	kindTreeNode
	kindGraphNode
	kindSlice
	kindVoid
)

const (
	arraySuffix = "[]"
	listPrefix  = "list<"
	listSuffix  = ">"
	voidType    = "void"
)

// dslType is a parsed type of the signature DSL (docs/specs/problem-format.md#type-dsl).
// `T[]` and `list<T>` both map to a Go slice, so they share kindSlice.
type dslType struct {
	kind kind
	elem *dslType
	text string
}

var namedKinds = map[string]kind{
	"int": kindInt, "long": kindLong, "double": kindDouble, "bool": kindBool,
	"string": kindString, "char": kindChar, "decimal": kindDecimal, "date": kindDate,
	"ListNode": kindListNode, "TreeNode": kindTreeNode, "GraphNode": kindGraphNode,
}

var goTypes = map[kind]reflect.Type{
	kindInt:       reflect.TypeFor[int](),
	kindLong:      reflect.TypeFor[int64](),
	kindDouble:    reflect.TypeFor[float64](),
	kindBool:      reflect.TypeFor[bool](),
	kindString:    reflect.TypeFor[string](),
	kindChar:      reflect.TypeFor[rune](),
	kindListNode:  reflect.TypeFor[*support.ListNode](),
	kindTreeNode:  reflect.TypeFor[*support.TreeNode](),
	kindGraphNode: reflect.TypeFor[*support.GraphNode](),
}

// parseType parses a value type; the CLI validated every signature, so only text that cannot be
// represented at all is rejected.
func parseType(text string) (*dslType, error) {
	if k, ok := namedKinds[text]; ok {
		return &dslType{kind: k, text: text}, nil
	}
	inner, ok := strings.CutSuffix(text, arraySuffix)
	if !ok {
		inner, ok = cutList(text)
	}
	if !ok {
		return nil, fmt.Errorf("unknown type %q", text)
	}
	elem, err := parseType(inner)
	if err != nil {
		return nil, err
	}
	return &dslType{kind: kindSlice, elem: elem, text: text}, nil
}

// parseReturn also accepts void.
func parseReturn(text string) (*dslType, error) {
	if text == voidType {
		return &dslType{kind: kindVoid, text: text}, nil
	}
	return parseType(text)
}

func cutList(text string) (string, bool) {
	rest, ok := strings.CutPrefix(text, listPrefix)
	if !ok {
		return "", false
	}
	return strings.CutSuffix(rest, listSuffix)
}

// unsupportedType is a DSL type the Go runner cannot represent yet: `decimal` and `date` need
// the vendored libraries of a later step (docs/decisions/0012-go-and-rust.md).
type unsupportedType struct{ text string }

func (e *unsupportedType) Error() string {
	return fmt.Sprintf("the Go runner does not support %s yet", e.text)
}

// goType is the one Go type the mapping table allows for t (docs/specs/problem-format.md
// #go-and-rust-mapping); nil for void.
func (t *dslType) goType() (reflect.Type, error) {
	switch t.kind {
	case kindVoid:
		return nil, nil
	case kindSlice:
		elem, err := t.elem.goType()
		if err != nil {
			return nil, err
		}
		return reflect.SliceOf(elem), nil
	case kindDecimal, kindDate:
		return nil, &unsupportedType{t.text}
	}
	return goTypes[t.kind], nil
}

func (t *dslType) isNode() bool {
	return t.kind == kindListNode || t.kind == kindTreeNode || t.kind == kindGraphNode
}
