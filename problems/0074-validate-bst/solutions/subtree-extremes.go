package validate_bst

import "cstudy/support"

type TreeNode = support.TreeNode

func isValidBST(root *TreeNode) bool {
	if root == nil {
		return true
	}
	if root.Left != nil && largest(root.Left) >= root.Val {
		return false
	}
	if root.Right != nil && smallest(root.Right) <= root.Val {
		return false
	}
	return isValidBST(root.Left) && isValidBST(root.Right)
}

// largest is the largest value anywhere in the subtree; it need not be a search tree, so
// scan it all.
func largest(node *TreeNode) int {
	best := node.Val
	for _, child := range []*TreeNode{node.Left, node.Right} {
		if child != nil {
			best = max(best, largest(child))
		}
	}
	return best
}

func smallest(node *TreeNode) int {
	best := node.Val
	for _, child := range []*TreeNode{node.Left, node.Right} {
		if child != nil {
			best = min(best, smallest(child))
		}
	}
	return best
}
