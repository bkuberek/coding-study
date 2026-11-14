package tree_path_sum_count

import "cstudy/support"

type TreeNode = support.TreeNode

func pathSum(root *TreeNode, targetSum int) int {
	// onPath[s] counts the prefixes of the current root path whose sum is s.
	onPath := map[int]int{0: 1}

	var countBelow func(node *TreeNode, total int) int
	countBelow = func(node *TreeNode, total int) int {
		if node == nil {
			return 0
		}
		total += node.Val
		found := onPath[total-targetSum]
		onPath[total]++
		found += countBelow(node.Left, total) + countBelow(node.Right, total)
		onPath[total]-- // leave the subtree: its prefix is no longer on the path
		return found
	}

	return countBelow(root, 0)
}
