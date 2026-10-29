package validate_bst

import "cstudy/support"

type TreeNode = support.TreeNode

func isValidBST(root *TreeNode) bool {
	var stack []*TreeNode
	node := root
	previous, hasPrevious := 0, false
	for len(stack) > 0 || node != nil {
		for node != nil {
			stack = append(stack, node)
			node = node.Left
		}
		node = stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		if hasPrevious && node.Val <= previous {
			return false
		}
		previous, hasPrevious = node.Val, true
		node = node.Right
	}
	return true
}
