package runner

import (
	"encoding/json"
	"fmt"

	"cstudy/support"
)

// maxListNodes bounds output lists: longer lists are reported as too long or cyclic.
const maxListNodes = 100_000

// Linked structures and their JSON encodings (docs/specs/problem-format.md, "Serialization of
// linked structures"). Inputs arrive as decoded JSON (json.Number for numbers).

// buildList reads `[1, 2, 3]`, or `{"values": [...], "cycle_at": k}` whose tail links back to
// node k.
func buildList(encoded any) (*support.ListNode, error) {
	values, cycleAt, err := listEncoding(encoded)
	if err != nil {
		return nil, err
	}
	nodes := make([]*support.ListNode, len(values))
	for i, value := range values {
		val, err := nodeInput(value)
		if err != nil {
			return nil, err
		}
		nodes[i] = &support.ListNode{Val: val}
		if i > 0 {
			nodes[i-1].Next = nodes[i]
		}
	}
	if len(nodes) == 0 {
		return nil, nil
	}
	if cycleAt >= 0 {
		nodes[len(nodes)-1].Next = nodes[cycleAt]
	}
	return nodes[0], nil
}

func listEncoding(encoded any) ([]any, int, error) {
	switch value := encoded.(type) {
	case []any:
		return value, -1, nil
	case map[string]any:
		values, ok := value["values"].([]any)
		cycleAt, isNumber := value["cycle_at"].(json.Number)
		if ok && isNumber {
			index, err := cycleAt.Int64()
			if err == nil && index >= 0 && index < int64(len(values)) {
				return values, int(index), nil
			}
		}
	}
	return nil, 0, &inputError{fmt.Sprintf("not a ListNode encoding: %s", describeJSON(encoded))}
}

// buildTree reads level order with null for missing children.
func buildTree(encoded any) (*support.TreeNode, error) {
	values, ok := encoded.([]any)
	if !ok {
		return nil, &inputError{fmt.Sprintf("expected an array for TreeNode, got %s", describeJSON(encoded))}
	}
	if len(values) == 0 || values[0] == nil {
		return nil, nil
	}
	rootVal, err := nodeInput(values[0])
	if err != nil {
		return nil, err
	}
	root := &support.TreeNode{Val: rootVal}
	parents := []*support.TreeNode{root}
	next := 1
	child := func() (*support.TreeNode, error) {
		if next >= len(values) {
			return nil, nil
		}
		value := values[next]
		next++
		if value == nil {
			return nil, nil
		}
		val, err := nodeInput(value)
		if err != nil {
			return nil, err
		}
		return &support.TreeNode{Val: val}, nil
	}
	for len(parents) > 0 {
		parent := parents[0]
		parents = parents[1:]
		if parent.Left, err = child(); err != nil {
			return nil, err
		}
		if parent.Right, err = child(); err != nil {
			return nil, err
		}
		for _, node := range []*support.TreeNode{parent.Left, parent.Right} {
			if node != nil {
				parents = append(parents, node)
			}
		}
	}
	return root, nil
}

// buildGraph reads a 1-indexed adjacency list where node i has value i, and returns node 1.
func buildGraph(encoded any) (*support.GraphNode, error) {
	adjacency, ok := encoded.([]any)
	if !ok {
		return nil, &inputError{fmt.Sprintf("expected an array for GraphNode, got %s", describeJSON(encoded))}
	}
	nodes := make([]*support.GraphNode, len(adjacency))
	for i := range nodes {
		nodes[i] = &support.GraphNode{Val: i + 1}
	}
	for i, entry := range adjacency {
		neighbors, ok := entry.([]any)
		if !ok {
			return nil, &inputError{fmt.Sprintf("expected an array for the neighbors of graph node %d, got %s", i+1, describeJSON(entry))}
		}
		nodes[i].Neighbors = make([]*support.GraphNode, 0, len(neighbors))
		for _, neighbor := range neighbors {
			index, err := neighborIndex(neighbor, len(nodes))
			if err != nil {
				return nil, err
			}
			nodes[i].Neighbors = append(nodes[i].Neighbors, nodes[index])
		}
	}
	if len(nodes) == 0 {
		return nil, nil
	}
	return nodes[0], nil
}

func neighborIndex(value any, count int) (int, error) {
	number, ok := value.(json.Number)
	index, err := number.Int64()
	if !ok || err != nil || index < 1 || index > int64(count) {
		return 0, &inputError{fmt.Sprintf("graph neighbor %s is not a node value 1..%d", describeJSON(value), count)}
	}
	return int(index - 1), nil
}

func nodeInput(value any) (int, error) {
	number, ok := value.(json.Number)
	if ok {
		if n, err := number.Int64(); err == nil {
			return int(n), nil
		}
	}
	return 0, &inputError{fmt.Sprintf("node value must be an int, got %s", describeJSON(value))}
}

func encodeList(head *support.ListNode) (any, error) {
	values := []any{}
	for node := head; node != nil; node = node.Next {
		if len(values) == maxListNodes {
			return nil, &invalidOutput{"list too long or cyclic"}
		}
		values = append(values, node.Val)
	}
	return values, nil
}

// encodeTree writes level order with null for missing children, trailing nulls trimmed.
func encodeTree(root *support.TreeNode) (any, error) {
	values := []any{}
	seen := map[*support.TreeNode]bool{}
	pending := []*support.TreeNode{root}
	for len(pending) > 0 {
		node := pending[0]
		pending = pending[1:]
		if node == nil {
			values = append(values, nil)
			continue
		}
		if seen[node] {
			return nil, &invalidOutput{"tree contains a cycle or a shared node"}
		}
		seen[node] = true
		values = append(values, node.Val)
		pending = append(pending, node.Left, node.Right)
	}
	for len(values) > 0 && values[len(values)-1] == nil {
		values = values[:len(values)-1]
	}
	return values, nil
}

// encodeGraph writes the neighbor values of nodes 1..k, where k nodes are reachable from start.
func encodeGraph(start *support.GraphNode) (any, error) {
	if start == nil {
		return []any{}, nil
	}
	byValue := map[int]*support.GraphNode{}
	seen := map[*support.GraphNode]bool{start: true}
	pending := []*support.GraphNode{start}
	for len(pending) > 0 {
		node := pending[0]
		pending = pending[1:]
		if _, taken := byValue[node.Val]; taken {
			return nil, &invalidOutput{fmt.Sprintf("graph has two nodes with value %d", node.Val)}
		}
		byValue[node.Val] = node
		for _, neighbor := range node.Neighbors {
			if neighbor == nil {
				return nil, &invalidOutput{"neighbors must not contain null"}
			}
			if !seen[neighbor] {
				seen[neighbor] = true
				pending = append(pending, neighbor)
			}
		}
	}
	adjacency := make([]any, len(byValue))
	for value := 1; value <= len(byValue); value++ {
		node, ok := byValue[value]
		if !ok {
			return nil, &invalidOutput{"graph node values must be exactly 1..k for k reachable nodes"}
		}
		neighbors := make([]any, len(node.Neighbors))
		for i, neighbor := range node.Neighbors {
			neighbors[i] = neighbor.Val
		}
		adjacency[value-1] = neighbors
	}
	return adjacency, nil
}

// traverse lists every node reachable from root, each once, in traversal order: list order,
// level order for trees, breadth-first for graphs (docs/specs/runners.md#node-modifiers). Nodes
// are pointers, so the result compares by identity.
func traverse(root any) []any {
	var order []any
	seen := map[any]bool{}
	pending := []any{root}
	for len(pending) > 0 {
		node := pending[0]
		pending = pending[1:]
		if isNilNode(node) || seen[node] {
			continue
		}
		seen[node] = true
		order = append(order, node)
		pending = append(pending, successors(node)...)
	}
	return order
}

func successors(node any) []any {
	switch n := node.(type) {
	case *support.ListNode:
		return []any{n.Next}
	case *support.TreeNode:
		return []any{n.Left, n.Right}
	case *support.GraphNode:
		next := make([]any, len(n.Neighbors))
		for i, neighbor := range n.Neighbors {
			next[i] = neighbor
		}
		return next
	}
	return nil
}

func isNilNode(node any) bool {
	switch n := node.(type) {
	case *support.ListNode:
		return n == nil
	case *support.TreeNode:
		return n == nil
	case *support.GraphNode:
		return n == nil
	}
	return node == nil
}

// nodeValue is the val of a node, for `ref_of` and `as: value`.
func nodeValue(node any) int {
	switch n := node.(type) {
	case *support.ListNode:
		return n.Val
	case *support.TreeNode:
		return n.Val
	case *support.GraphNode:
		return n.Val
	}
	return 0
}
