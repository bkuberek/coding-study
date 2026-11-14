package right_side_view

import "cstudy/support"

type TreeNode = support.TreeNode

func rightSideView(root *TreeNode) []int {
	var view []int
	var queue []*TreeNode
	if root != nil {
		queue = append(queue, root)
	}
	for len(queue) > 0 {
		// The node at the back of the queue is the last one of the current level.
		view = append(view, queue[len(queue)-1].Val)
		for range len(queue) {
			node := queue[0]
			queue = queue[1:]
			if node.Left != nil {
				queue = append(queue, node.Left)
			}
			if node.Right != nil {
				queue = append(queue, node.Right)
			}
		}
	}
	return view
}
