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
	var out strings.Builder
	var write func(node *TreeNode)
	write = func(node *TreeNode) {
		if out.Len() > 0 {
			out.WriteString(separator)
		}
		if node == nil {
			out.WriteString(missing)
			return
		}
		out.WriteString(strconv.Itoa(node.Val))
		write(node.Left)
		write(node.Right)
	}
	write(root)
	return out.String()
}

func deserialize(data string) *TreeNode {
	tokens := strings.Split(data, separator)
	next := 0
	var read func() *TreeNode
	read = func() *TreeNode {
		token := tokens[next]
		next++
		if token == missing {
			return nil
		}
		node := &TreeNode{Val: parse(token)}
		node.Left = read()
		node.Right = read()
		return node
	}
	return read()
}

func parse(token string) int {
	value, err := strconv.Atoi(token)
	if err != nil {
		panic(err)
	}
	return value
}
