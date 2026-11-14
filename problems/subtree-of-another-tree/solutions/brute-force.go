package subtree_of_another_tree

import "cstudy/support"

type TreeNode = support.TreeNode

func isSubtree(root *TreeNode, subRoot *TreeNode) bool {
	if root == nil {
		return false
	}
	return same(root, subRoot) || isSubtree(root.Left, subRoot) || isSubtree(root.Right, subRoot)
}

func same(a, b *TreeNode) bool {
	if a == nil || b == nil {
		return a == b
	}
	return a.Val == b.Val && same(a.Left, b.Left) && same(a.Right, b.Right)
}
