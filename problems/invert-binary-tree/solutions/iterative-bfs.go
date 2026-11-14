package invert_binary_tree

import "cstudy/support"

type TreeNode = support.TreeNode

func invertTree(root *TreeNode) *TreeNode {
	if root == nil {
		return nil
	}
	pending := []*TreeNode{root}
	for len(pending) > 0 {
		node := pending[0]
		pending = pending[1:]
		node.Left, node.Right = node.Right, node.Left
		if node.Left != nil {
			pending = append(pending, node.Left)
		}
		if node.Right != nil {
			pending = append(pending, node.Right)
		}
	}
	return root
}
