// Package support holds the node types of the signature DSL (docs/specs/problem-format.md
// #support-classes). Stubs alias them, so solutions read like LeetCode:
//
//	type ListNode = support.ListNode
//
// The runner builds inputs from these types and reads outputs through them; a solution must use
// these exact types, not look-alike structs.
package support

// ListNode is a node of a singly linked list; a nil *ListNode is the empty list.
type ListNode struct {
	Val  int
	Next *ListNode
}

// TreeNode is a node of a binary tree; a nil *TreeNode is the empty tree.
type TreeNode struct {
	Val   int
	Left  *TreeNode
	Right *TreeNode
}

// GraphNode is a node of an undirected graph given as an adjacency list.
type GraphNode struct {
	Val       int
	Neighbors []*GraphNode
}
