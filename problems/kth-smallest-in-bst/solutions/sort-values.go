package kth_smallest_in_bst

import (
	"slices"

	"cstudy/support"
)

type TreeNode = support.TreeNode

func kthSmallest(root *TreeNode, k int) int {
	var values []int
	pending := []*TreeNode{root}
	for len(pending) > 0 {
		node := pending[len(pending)-1]
		pending = pending[:len(pending)-1]
		if node != nil {
			values = append(values, node.Val)
			pending = append(pending, node.Left, node.Right)
		}
	}
	slices.Sort(values)
	return values[k-1]
}
