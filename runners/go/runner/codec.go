package runner

import (
	"bytes"
	"encoding/json"
	"fmt"
	"math"
	"reflect"
	"strconv"
	"unicode/utf8"

	"cstudy/support"
)

const (
	maxSafeInteger  = 1<<53 - 1
	maxBMPCodePoint = 0xFFFF
)

// inputError is a case input that does not fit the declared type (error type "InvalidInput").
type inputError struct{ message string }

func (e *inputError) Error() string { return e.message }

// invalidOutput is a returned value that cannot be serialized as the declared type.
type invalidOutput struct{ reason string }

func (e *invalidOutput) Error() string { return e.reason }

// parseJSON reads raw JSON keeping numbers exact (json.Number).
func parseJSON(raw json.RawMessage) (any, error) {
	if raw == nil {
		return nil, &inputError{"missing argument"}
	}
	decoder := json.NewDecoder(bytes.NewReader(raw))
	decoder.UseNumber()
	var value any
	if err := decoder.Decode(&value); err != nil {
		return nil, &inputError{err.Error()}
	}
	return value, nil
}

// decode builds a fresh Go value of t's Go type from parsed JSON. The CLI validated the
// content, but a value of the wrong shape is still an input error, never a panic.
func decode(value any, t *dslType) (reflect.Value, error) {
	switch t.kind {
	case kindInt:
		n, err := integer(value, t, 32)
		return reflect.ValueOf(int(n)), err
	case kindLong:
		n, err := integer(value, t, 64)
		return reflect.ValueOf(n), err
	case kindDouble:
		number, ok := value.(json.Number)
		if !ok {
			return reflect.Value{}, mismatch(value, t)
		}
		f, err := number.Float64()
		if err != nil {
			return reflect.Value{}, mismatch(value, t)
		}
		return reflect.ValueOf(f), nil
	case kindBool:
		b, ok := value.(bool)
		if !ok {
			return reflect.Value{}, mismatch(value, t)
		}
		return reflect.ValueOf(b), nil
	case kindString:
		s, ok := value.(string)
		if !ok {
			return reflect.Value{}, mismatch(value, t)
		}
		return reflect.ValueOf(s), nil
	case kindChar:
		s, ok := value.(string)
		r, size := utf8.DecodeRuneInString(s)
		if !ok || size != len(s) || r == utf8.RuneError || r > maxBMPCodePoint {
			return reflect.Value{}, mismatch(value, t)
		}
		return reflect.ValueOf(r), nil
	case kindListNode:
		node, err := buildList(value)
		return reflect.ValueOf(node), err
	case kindTreeNode:
		node, err := buildTree(value)
		return reflect.ValueOf(node), err
	case kindGraphNode:
		node, err := buildGraph(value)
		return reflect.ValueOf(node), err
	case kindSlice:
		return decodeSlice(value, t)
	}
	return reflect.Value{}, &unsupportedType{t.text}
}

func decodeSlice(value any, t *dslType) (reflect.Value, error) {
	items, ok := value.([]any)
	if !ok {
		return reflect.Value{}, mismatch(value, t)
	}
	sliceType, err := t.goType()
	if err != nil {
		return reflect.Value{}, err
	}
	slice := reflect.MakeSlice(sliceType, len(items), len(items))
	for i, item := range items {
		element, err := decode(item, t.elem)
		if err != nil {
			return reflect.Value{}, err
		}
		slice.Index(i).Set(element)
	}
	return slice, nil
}

func integer(value any, t *dslType, bits int) (int64, error) {
	number, ok := value.(json.Number)
	if !ok {
		return 0, mismatch(value, t)
	}
	n, err := strconv.ParseInt(number.String(), 10, bits)
	if err != nil {
		return 0, &inputError{fmt.Sprintf("expected %s, got %s", t.text, number)}
	}
	return n, nil
}

func mismatch(value any, t *dslType) error {
	return &inputError{fmt.Sprintf("expected %s, got %s", t.text, describeJSON(value))}
}

// describeJSON shows a decoded JSON value in error messages.
func describeJSON(value any) string {
	text, err := json.Marshal(value)
	if err != nil {
		return fmt.Sprint(value)
	}
	return string(text)
}

// encode turns a returned Go value into JSON-ready data. Its Go type was checked against the
// signature when the target loaded, so only range, finiteness, encoding and structure can fail.
// location is the element's position, e.g. `[2][0]`, which prefixes the reason of an invalid
// output.
func encode(value reflect.Value, t *dslType, location string) (any, error) {
	if t.kind == kindSlice {
		// A nil slice is Go's idiomatic empty result; encoding/json would write null.
		items := make([]any, value.Len())
		for i := range items {
			item, err := encode(value.Index(i), t.elem, fmt.Sprintf("%s[%d]", location, i))
			if err != nil {
				return nil, err
			}
			items[i] = item
		}
		return items, nil
	}
	encoded, err := encodeValue(value, t)
	if invalid, ok := err.(*invalidOutput); ok && location != "" {
		return nil, &invalidOutput{location + ": " + invalid.reason}
	}
	return encoded, err
}

func encodeValue(value reflect.Value, t *dslType) (any, error) {
	switch t.kind {
	case kindInt:
		n := value.Int()
		if n < math.MinInt32 || n > math.MaxInt32 {
			return nil, &invalidOutput{fmt.Sprintf("int out of range: %d", n)}
		}
		return n, nil
	case kindLong:
		n := value.Int()
		if n < -maxSafeInteger || n > maxSafeInteger {
			return nil, &invalidOutput{fmt.Sprintf("long out of range: %d", n)}
		}
		return n, nil
	case kindDouble:
		f := value.Float()
		if math.IsNaN(f) || math.IsInf(f, 0) {
			return nil, &invalidOutput{fmt.Sprintf("non-finite double: %v", f)}
		}
		return f, nil
	case kindBool:
		return value.Bool(), nil
	case kindString:
		s := value.String()
		if !utf8.ValidString(s) {
			return nil, &invalidOutput{fmt.Sprintf("string is not valid UTF-8: %q", s)}
		}
		return s, nil
	case kindChar:
		r := rune(value.Int())
		if !utf8.ValidRune(r) || r > maxBMPCodePoint {
			return nil, &invalidOutput{fmt.Sprintf("expected char, got the code point %d", r)}
		}
		return string(r), nil
	case kindListNode:
		return encodeList(value.Interface().(*support.ListNode))
	case kindTreeNode:
		return encodeTree(value.Interface().(*support.TreeNode))
	case kindGraphNode:
		return encodeGraph(value.Interface().(*support.GraphNode))
	case kindVoid:
		return nil, nil
	}
	return nil, &unsupportedType{t.text}
}
