package tree_path_sum_count

import "cstudy/support"

type TreeNode = support.TreeNode

// walk is a node together with the sum of the downward path that ends at it.
type walk struct {
	node  *TreeNode
	total int
}

func pathSum(root *TreeNode, targetSum int) int {
	count := 0
	var starts []*TreeNode
	if root != nil {
		starts = append(starts, root)
	}
	for len(starts) > 0 {
		start := starts[len(starts)-1]
		starts = starts[:len(starts)-1]
		// Walk every downward path from start, carrying the sum so far.
		pending := []walk{{start, start.Val}}
		for len(pending) > 0 {
			current := pending[len(pending)-1]
			pending = pending[:len(pending)-1]
			if current.total == targetSum {
				count++
			}
			for _, child := range []*TreeNode{current.node.Left, current.node.Right} {
				if child != nil {
					pending = append(pending, walk{child, current.total + child.Val})
				}
			}
		}
		for _, child := range []*TreeNode{start.Left, start.Right} {
			if child != nil {
				starts = append(starts, child)
			}
		}
	}
	return count
}
