package tree_from_preorder_inorder

import (
	"slices"

	"cstudy/support"
)

type TreeNode = support.TreeNode

func buildTree(preorder []int, inorder []int) *TreeNode {
	// build returns the tree of the size values at preorder[preStart:] and inorder[inStart:].
	var build func(preStart, inStart, size int) *TreeNode
	build = func(preStart, inStart, size int) *TreeNode {
		if size == 0 {
			return nil
		}
		value := preorder[preStart]
		// The root's position inside this window of inorder: a linear scan.
		split := inStart + slices.Index(inorder[inStart:inStart+size], value)
		leftSize := split - inStart
		return &TreeNode{
			Val:   value,
			Left:  build(preStart+1, inStart, leftSize),
			Right: build(preStart+1+leftSize, split+1, size-leftSize-1),
		}
	}
	return build(0, 0, len(preorder))
}
