package right_side_view

import "cstudy/support"

type TreeNode = support.TreeNode

func rightSideView(root *TreeNode) []int {
	var view []int
	var visit func(node *TreeNode, depth int)
	visit = func(node *TreeNode, depth int) {
		if node == nil {
			return
		}
		if depth == len(view) {
			view = append(view, node.Val)
		}
		visit(node.Right, depth+1)
		visit(node.Left, depth+1)
	}
	visit(root, 0)
	return view
}
