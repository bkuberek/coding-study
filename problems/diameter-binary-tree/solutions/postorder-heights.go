package diameter_binary_tree

import "cstudy/support"

type TreeNode = support.TreeNode

func diameterOfBinaryTree(root *TreeNode) int {
	best := 0
	var height func(node *TreeNode) int
	height = func(node *TreeNode) int {
		if node == nil {
			return 0
		}
		left, right := height(node.Left), height(node.Right)
		best = max(best, left+right)
		return 1 + max(left, right)
	}
	height(root)
	return best
}
