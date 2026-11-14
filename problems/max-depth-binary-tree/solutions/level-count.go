package max_depth_binary_tree

import "cstudy/support"

type TreeNode = support.TreeNode

func maxDepth(root *TreeNode) int {
	var level []*TreeNode
	if root != nil {
		level = append(level, root)
	}
	depth := 0
	for len(level) > 0 {
		depth++
		// Drain exactly the nodes of the current level; their children form the next one.
		for range len(level) {
			node := level[0]
			level = level[1:]
			if node.Left != nil {
				level = append(level, node.Left)
			}
			if node.Right != nil {
				level = append(level, node.Right)
			}
		}
	}
	return depth
}
