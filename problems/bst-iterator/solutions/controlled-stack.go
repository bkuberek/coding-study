package bst_iterator

import "cstudy/support"

type TreeNode = support.TreeNode

type BSTIterator struct {
	// Nodes whose left subtree is finished (or about to be) and that are not returned yet.
	stack []*TreeNode
}

func NewBSTIterator(root *TreeNode) *BSTIterator {
	iterator := &BSTIterator{}
	iterator.pushLeftSpine(root)
	return iterator
}

func (i *BSTIterator) pushLeftSpine(node *TreeNode) {
	for ; node != nil; node = node.Left {
		i.stack = append(i.stack, node)
	}
}

func (i *BSTIterator) Next() int {
	node := i.stack[len(i.stack)-1]
	i.stack = i.stack[:len(i.stack)-1]
	i.pushLeftSpine(node.Right)
	return node.Val
}

func (i *BSTIterator) HasNext() bool {
	return len(i.stack) > 0
}
