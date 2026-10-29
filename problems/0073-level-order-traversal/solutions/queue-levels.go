package level_order_traversal

import "cstudy/support"

type TreeNode = support.TreeNode

func levelOrder(root *TreeNode) [][]int {
	var levels [][]int
	var queue []*TreeNode
	if root != nil {
		queue = append(queue, root)
	}
	for len(queue) > 0 {
		level := make([]int, 0, len(queue))
		for range len(queue) {
			node := queue[0]
			queue = queue[1:]
			level = append(level, node.Val)
			if node.Left != nil {
				queue = append(queue, node.Left)
			}
			if node.Right != nil {
				queue = append(queue, node.Right)
			}
		}
		levels = append(levels, level)
	}
	return levels
}
