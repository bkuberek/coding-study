package kth_smallest_in_bst

import "cstudy/support"

type TreeNode = support.TreeNode

func kthSmallest(root *TreeNode, k int) int {
	var stack []*TreeNode
	node := root
	for {
		for node != nil {
			stack = append(stack, node)
			node = node.Left
		}
		node = stack[len(stack)-1]
		stack = stack[:len(stack)-1]
		k--
		if k == 0 {
			return node.Val
		}
		node = node.Right
	}
}
