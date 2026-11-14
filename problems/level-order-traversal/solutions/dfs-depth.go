package level_order_traversal

import "cstudy/support"

type TreeNode = support.TreeNode

func levelOrder(root *TreeNode) [][]int {
	type entry struct {
		node  *TreeNode
		depth int
	}
	var levels [][]int
	// Pre-order with an explicit stack; pushing right before left visits left first.
	var pending []entry
	if root != nil {
		pending = append(pending, entry{root, 0})
	}
	for len(pending) > 0 {
		top := pending[len(pending)-1]
		pending = pending[:len(pending)-1]
		if top.depth == len(levels) {
			levels = append(levels, nil)
		}
		levels[top.depth] = append(levels[top.depth], top.node.Val)
		if top.node.Right != nil {
			pending = append(pending, entry{top.node.Right, top.depth + 1})
		}
		if top.node.Left != nil {
			pending = append(pending, entry{top.node.Left, top.depth + 1})
		}
	}
	return levels
}
