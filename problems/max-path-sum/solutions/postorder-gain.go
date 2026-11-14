package max_path_sum

import "cstudy/support"

type TreeNode = support.TreeNode

func maxPathSum(root *TreeNode) int {
	best := root.Val
	// gain is the best downward path sum from node, recording the best path turning at it.
	var gain func(node *TreeNode) int
	gain = func(node *TreeNode) int {
		if node == nil {
			return 0
		}
		left := max(0, gain(node.Left))
		right := max(0, gain(node.Right))
		best = max(best, node.Val+left+right)
		return node.Val + max(left, right)
	}
	gain(root)
	return best
}
