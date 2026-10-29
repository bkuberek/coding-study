package runner

import (
	"encoding/json"
	"math"
	"reflect"
	"strings"
	"testing"

	"cstudy/support"
)

func mustType(t *testing.T, text string) *dslType {
	t.Helper()
	parsed, err := parseReturn(text)
	if err != nil {
		t.Fatalf("parse %q: %v", text, err)
	}
	return parsed
}

func roundTrip(t *testing.T, typeText, input string) string {
	t.Helper()
	declared := mustType(t, typeText)
	parsed, err := parseJSON(json.RawMessage(input))
	if err != nil {
		t.Fatalf("parse %s: %v", input, err)
	}
	value, err := decode(parsed, declared)
	if err != nil {
		t.Fatalf("decode %s as %s: %v", input, typeText, err)
	}
	encoded, err := encode(value, declared, "")
	if err != nil {
		t.Fatalf("encode %s as %s: %v", input, typeText, err)
	}
	return string(marshal(encoded))
}

func TestEveryTypeRoundTrips(t *testing.T) {
	tests := []struct {
		typeText string
		input    string
		want     string
	}{
		{"int", "-2147483648", "-2147483648"},
		{"long", "9007199254740991", "9007199254740991"},
		{"double", "1e-09", "1e-9"},
		{"double", "1.7976931348623157e+308", "1.7976931348623157e+308"},
		{"bool", "false", "false"},
		{"string", `"üñí \"quoted\" \\ line\nbreak"`, `"üñí \"quoted\" \\ line\nbreak"`},
		{"char", `"€"`, `"€"`},
		{"int[]", "[]", "[]"},
		{"char[]", `["a","b"]`, `["a","b"]`},
		{"string[][]", `[["a"],[]]`, `[["a"],[]]`},
		{"list<list<list<int>>>", "[[[1],[2,3]],[]]", "[[[1],[2,3]],[]]"},
		{"ListNode", "[1,2,3]", "[1,2,3]"},
		{"ListNode", "[]", "[]"},
		{"TreeNode", "[3,9,20,null,null,15,7]", "[3,9,20,null,null,15,7]"},
		{"TreeNode", "[1,null,2]", "[1,null,2]"},
		{"TreeNode", "[]", "[]"},
		{"GraphNode", "[[2,4],[1,3],[2,4],[1,3]]", "[[2,4],[1,3],[2,4],[1,3]]"},
		{"GraphNode", "[[]]", "[[]]"},
		{"GraphNode", "[]", "[]"},
		{"ListNode[]", "[[1,2],[],[3]]", "[[1,2],[],[3]]"},
		{"list<TreeNode>", "[[1,2],[]]", "[[1,2],[]]"},
	}
	for _, tt := range tests {
		t.Run(tt.typeText+" "+tt.input, func(t *testing.T) {
			if got := roundTrip(t, tt.typeText, tt.input); got != tt.want {
				t.Errorf("got %s, want %s", got, tt.want)
			}
		})
	}
}

func TestNilSliceEncodesAsAnEmptyArray(t *testing.T) {
	encoded, err := encode(reflect.ValueOf([]int(nil)), mustType(t, "int[]"), "")
	if err != nil || string(marshal(encoded)) != "[]" {
		t.Errorf("got %s, %v; want []", marshal(encoded), err)
	}
}

func TestInvalidOutputs(t *testing.T) {
	cycle := &support.ListNode{Val: 1}
	cycle.Next = cycle
	shared := &support.TreeNode{Val: 2}
	tests := []struct {
		name     string
		typeText string
		value    any
		reason   string
	}{
		{"int out of range", "int", 1 << 31, "int out of range: 2147483648"},
		{"long beyond 2^53", "long", int64(1 << 53), "long out of range: 9007199254740992"},
		{"infinity", "double", math.Inf(1), "non-finite double: +Inf"},
		{"NaN", "double", math.NaN(), "non-finite double: NaN"},
		{"astral char", "char", '😀', "expected char, got the code point 128512"},
		{"invalid UTF-8", "string", "\xff", `string is not valid UTF-8: "\xff"`},
		{"located element", "int[][]", [][]int{{1}, {2, 1 << 40}}, "[1][1]: int out of range: 1099511627776"},
		{"cyclic list", "ListNode", cycle, "list too long or cyclic"},
		{"shared tree node", "TreeNode", &support.TreeNode{Val: 1, Left: shared, Right: shared}, "tree contains a cycle or a shared node"},
		{"graph values not 1..k", "GraphNode", &support.GraphNode{Val: 5}, "graph node values must be exactly 1..k for k reachable nodes"},
		{"nil neighbor", "GraphNode", &support.GraphNode{Val: 1, Neighbors: []*support.GraphNode{nil}}, "neighbors must not contain null"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			_, err := encode(reflect.ValueOf(tt.value), mustType(t, tt.typeText), "")
			if err == nil || err.Error() != tt.reason {
				t.Errorf("got %v, want %q", err, tt.reason)
			}
		})
	}
}

func TestInvalidInputs(t *testing.T) {
	tests := []struct {
		typeText string
		input    string
		message  string
	}{
		{"int", "2147483648", "expected int, got 2147483648"},
		{"int", `"1"`, `expected int, got "1"`},
		{"char", `"ab"`, `expected char, got "ab"`},
		{"ListNode", `{"values":[1],"cycle_at":3}`, `not a ListNode encoding: {"cycle_at":3,"values":[1]}`},
		{"GraphNode", "[[3]]", "graph neighbor 3 is not a node value 1..1"},
	}
	for _, tt := range tests {
		t.Run(tt.typeText+" "+tt.input, func(t *testing.T) {
			parsed, err := parseJSON(json.RawMessage(tt.input))
			if err != nil {
				t.Fatal(err)
			}
			_, err = decode(parsed, mustType(t, tt.typeText))
			if err == nil || err.Error() != tt.message {
				t.Errorf("got %v, want %q", err, tt.message)
			}
		})
	}
}

func TestCyclicListInputLinksTheTailBack(t *testing.T) {
	head, err := buildList(map[string]any{"values": []any{json.Number("3"), json.Number("2"), json.Number("0")}, "cycle_at": json.Number("1")})
	if err != nil {
		t.Fatal(err)
	}
	if head.Next.Next.Next != head.Next {
		t.Error("the tail does not link back to node 1")
	}
	if got := len(traverse(head)); got != 3 {
		t.Errorf("traversal visits %d nodes, want 3", got)
	}
}

func TestDecimalAndDateAreNotSupportedYet(t *testing.T) {
	for _, text := range []string{"decimal", "date[]", "list<decimal>"} {
		_, err := mustType(t, text).goType()
		if err == nil || !strings.Contains(err.Error(), "does not support") {
			t.Errorf("%s: got %v, want an unsupported type", text, err)
		}
	}
}

func TestTruncationKeepsWholeCharacters(t *testing.T) {
	tests := []struct {
		name  string
		kept  string
		total int
		want  string
	}{
		{"short", "hello", 5, "hello"},
		{"exactly the limit", strings.Repeat("x", maxOutputBytes), maxOutputBytes, strings.Repeat("x", maxOutputBytes)},
		{"over the limit", strings.Repeat("x", keptBytes), 9000, strings.Repeat("x", maxOutputBytes) + truncationNotice},
		{"split character", strings.Repeat("x", maxOutputBytes-1) + "€", 9000, strings.Repeat("x", maxOutputBytes-1) + truncationNotice},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := truncated([]byte(tt.kept), tt.total); got != tt.want {
				t.Errorf("got %d bytes, want %d", len(got), len(tt.want))
			}
		})
	}
}
