package tree_from_preorder_inorder

import "cstudy/support"

type TreeNode = support.TreeNode

func buildTree(preorder []int, inorder []int) *TreeNode {
	position := make(map[int]int, len(inorder))
	for index, value := range inorder {
		position[value] = index
	}
	nextRoot := 0
	// build returns the tree whose in-order walk is inorder[low:high]; its root is the next
	// pre-order value.
	var build func(low, high int) *TreeNode
	build = func(low, high int) *TreeNode {
		if low == high {
			return nil
		}
		value := preorder[nextRoot]
		nextRoot++
		split := position[value]
		node := &TreeNode{Val: value}
		node.Left = build(low, split)
		node.Right = build(split+1, high)
		return node
	}
	return build(0, len(inorder))
}
