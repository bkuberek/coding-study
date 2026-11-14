package max_path_sum

import "cstudy/support"

type TreeNode = support.TreeNode

func maxPathSum(root *TreeNode) int {
	turningHere := root.Val + max(0, gain(root.Left)) + max(0, gain(root.Right))
	best := turningHere
	for _, child := range []*TreeNode{root.Left, root.Right} {
		if child != nil {
			best = max(best, maxPathSum(child))
		}
	}
	return best
}

// gain is the largest sum of a path that starts at node and only goes down (0 for no node).
func gain(node *TreeNode) int {
	if node == nil {
		return 0
	}
	return node.Val + max(0, gain(node.Left), gain(node.Right))
}
