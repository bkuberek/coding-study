package validate_bst

import "cstudy/support"

type TreeNode = support.TreeNode

func isValidBST(root *TreeNode) bool {
	return within(root, nil, nil)
}

// within reports whether every value of the subtree is strictly between low and high (nil:
// unbounded). A *int stands for "optional int", and &node.Val points at the node's own field.
func within(node *TreeNode, low, high *int) bool {
	if node == nil {
		return true
	}
	if (low != nil && node.Val <= *low) || (high != nil && node.Val >= *high) {
		return false
	}
	return within(node.Left, low, &node.Val) && within(node.Right, &node.Val, high)
}
