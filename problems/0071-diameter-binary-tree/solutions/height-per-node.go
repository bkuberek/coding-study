package diameter_binary_tree

import "cstudy/support"

type TreeNode = support.TreeNode

func diameterOfBinaryTree(root *TreeNode) int {
	if root == nil {
		return 0
	}
	turningHere := height(root.Left) + height(root.Right)
	return max(turningHere, diameterOfBinaryTree(root.Left), diameterOfBinaryTree(root.Right))
}

// height is the number of nodes on the longest downward path from node.
func height(node *TreeNode) int {
	if node == nil {
		return 0
	}
	return 1 + max(height(node.Left), height(node.Right))
}
