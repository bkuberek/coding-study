package balanced_binary_tree

import "cstudy/support"

type TreeNode = support.TreeNode

func isBalanced(root *TreeNode) bool {
	if root == nil {
		return true
	}
	gap := height(root.Left) - height(root.Right)
	return -1 <= gap && gap <= 1 && isBalanced(root.Left) && isBalanced(root.Right)
}

func height(node *TreeNode) int {
	if node == nil {
		return 0
	}
	return 1 + max(height(node.Left), height(node.Right))
}
