package max_depth_binary_tree

import "cstudy/support"

type TreeNode = support.TreeNode

func maxDepth(root *TreeNode) int {
	if root == nil {
		return 0
	}
	return 1 + max(maxDepth(root.Left), maxDepth(root.Right))
}
