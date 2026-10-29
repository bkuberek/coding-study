package subtree_of_another_tree

import "cstudy/support"

type TreeNode = support.TreeNode

// token is one entry of a pre-order description: a value, or a missing child. Go has no
// optional integer, and a comparable struct makes `==` work on tokens.
type token struct {
	val     int
	missing bool
}

func isSubtree(root *TreeNode, subRoot *TreeNode) bool {
	return occurs(tokens(subRoot), tokens(root))
}

// tokens lists the pre-order values with a missing token for every absent child: a unique
// description of the tree.
func tokens(root *TreeNode) []token {
	var result []token
	pending := []*TreeNode{root}
	for len(pending) > 0 {
		node := pending[len(pending)-1]
		pending = pending[:len(pending)-1]
		if node == nil {
			result = append(result, token{missing: true})
			continue
		}
		result = append(result, token{val: node.Val})
		pending = append(pending, node.Right, node.Left)
	}
	return result
}

// occurs is Knuth-Morris-Pratt: does pattern occur as a contiguous block of text?
func occurs(pattern, text []token) bool {
	border := make([]int, len(pattern))
	length := 0
	for i := 1; i < len(pattern); i++ {
		for length > 0 && pattern[i] != pattern[length] {
			length = border[length-1]
		}
		if pattern[i] == pattern[length] {
			length++
		}
		border[i] = length
	}
	matched := 0
	for _, t := range text {
		for matched > 0 && t != pattern[matched] {
			matched = border[matched-1]
		}
		if t == pattern[matched] {
			matched++
			if matched == len(pattern) {
				return true
			}
		}
	}
	return false
}
