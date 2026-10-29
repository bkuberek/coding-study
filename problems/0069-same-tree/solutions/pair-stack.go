package same_tree

import "cstudy/support"

type TreeNode = support.TreeNode

func isSameTree(p *TreeNode, q *TreeNode) bool {
	type pair struct{ a, b *TreeNode }
	pending := []pair{{p, q}}
	for len(pending) > 0 {
		top := pending[len(pending)-1]
		pending = pending[:len(pending)-1]
		a, b := top.a, top.b
		if a == nil && b == nil {
			continue
		}
		if a == nil || b == nil || a.Val != b.Val {
			return false
		}
		pending = append(pending, pair{a.Right, b.Right}, pair{a.Left, b.Left})
	}
	return true
}
