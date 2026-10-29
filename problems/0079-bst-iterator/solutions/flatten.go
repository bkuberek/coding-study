package bst_iterator

import "cstudy/support"

type TreeNode = support.TreeNode

type BSTIterator struct {
	values   []int
	position int
}

func NewBSTIterator(root *TreeNode) *BSTIterator {
	iterator := &BSTIterator{}
	iterator.collect(root)
	return iterator
}

func (i *BSTIterator) collect(node *TreeNode) {
	if node != nil {
		i.collect(node.Left)
		i.values = append(i.values, node.Val)
		i.collect(node.Right)
	}
}

func (i *BSTIterator) Next() int {
	value := i.values[i.position]
	i.position++
	return value
}

func (i *BSTIterator) HasNext() bool {
	return i.position < len(i.values)
}
