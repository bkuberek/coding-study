package serialize_binary_tree

import (
	"strconv"
	"strings"

	"cstudy/support"
)

type TreeNode = support.TreeNode

const (
	missing   = "#"
	separator = ","
)

func serializeDeserialize(root *TreeNode) *TreeNode {
	return deserialize(serialize(root))
}

func serialize(root *TreeNode) string {
	var tokens []string
	queue := []*TreeNode{root}
	for len(queue) > 0 {
		node := queue[0]
		queue = queue[1:]
		if node == nil {
			tokens = append(tokens, missing)
			continue
		}
		tokens = append(tokens, strconv.Itoa(node.Val))
		queue = append(queue, node.Left, node.Right)
	}
	return strings.Join(tokens, separator)
}

func deserialize(data string) *TreeNode {
	tokens := strings.Split(data, separator)
	if tokens[0] == missing {
		return nil
	}
	root := &TreeNode{Val: parse(tokens[0])}
	queue := []*TreeNode{root}
	position := 1
	// Every node was written with exactly two child tokens, in queue order.
	for len(queue) > 0 {
		node := queue[0]
		queue = queue[1:]
		if left := tokens[position]; left != missing {
			node.Left = &TreeNode{Val: parse(left)}
			queue = append(queue, node.Left)
		}
		if right := tokens[position+1]; right != missing {
			node.Right = &TreeNode{Val: parse(right)}
			queue = append(queue, node.Right)
		}
		position += 2
	}
	return root
}

func parse(token string) int {
	value, err := strconv.Atoi(token)
	if err != nil {
		panic(err)
	}
	return value
}
