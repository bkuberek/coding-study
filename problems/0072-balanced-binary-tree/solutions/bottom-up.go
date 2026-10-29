package balanced_binary_tree

import "cstudy/support"

type TreeNode = support.TreeNode

const unbalanced = -1

func isBalanced(root *TreeNode) bool {
	return checkedHeight(root) != unbalanced
}

// checkedHeight is the height of node, or unbalanced as soon as any subtree below it is
// unbalanced.
func checkedHeight(node *TreeNode) int {
	if node == nil {
		return 0
	}
	left := checkedHeight(node.Left)
	if left == unbalanced {
		return unbalanced
	}
	right := checkedHeight(node.Right)
	if right == unbalanced || left-right > 1 || right-left > 1 {
		return unbalanced
	}
	return 1 + max(left, right)
}
