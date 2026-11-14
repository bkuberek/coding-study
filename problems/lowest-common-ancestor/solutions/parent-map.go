package lowest_common_ancestor

import "cstudy/support"

type TreeNode = support.TreeNode

func lowestCommonAncestor(root *TreeNode, p *TreeNode, q *TreeNode) *TreeNode {
	// Pointers are comparable, so nodes can be map keys directly.
	parent := map[*TreeNode]*TreeNode{root: nil}
	known := func(node *TreeNode) bool {
		_, ok := parent[node]
		return ok
	}
	pending := []*TreeNode{root}
	for !known(p) || !known(q) {
		current := pending[len(pending)-1]
		pending = pending[:len(pending)-1]
		for _, child := range []*TreeNode{current.Left, current.Right} {
			if child != nil {
				parent[child] = current
				pending = append(pending, child)
			}
		}
	}
	ancestorsOfP := make(map[*TreeNode]bool)
	for node := p; node != nil; node = parent[node] {
		ancestorsOfP[node] = true
	}
	node := q
	for !ancestorsOfP[node] {
		node = parent[node]
	}
	return node
}
