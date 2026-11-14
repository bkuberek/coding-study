package lowest_common_ancestor

import "cstudy/support"

type TreeNode = support.TreeNode

// lowestCommonAncestor returns the answer if both p and q are below root, else whichever of
// them is below, else nil. Pointers compare by identity.
func lowestCommonAncestor(root *TreeNode, p *TreeNode, q *TreeNode) *TreeNode {
	if root == nil || root == p || root == q {
		return root
	}
	left := lowestCommonAncestor(root.Left, p, q)
	right := lowestCommonAncestor(root.Right, p, q)
	if left != nil && right != nil {
		return root
	}
	if left != nil {
		return left
	}
	return right
}
