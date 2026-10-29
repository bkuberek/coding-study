package sort_linked_list

import "cstudy/support"

type ListNode = support.ListNode

func sortList(head *ListNode) *ListNode {
	length := 0
	for node := head; node != nil; node = node.Next {
		length++
	}
	dummy := &ListNode{Next: head}
	// After the pass with width w, the list is a sequence of sorted runs of length 2w.
	for width := 1; width < length; width *= 2 {
		tail := dummy
		rest := dummy.Next
		for rest != nil {
			left := rest
			right := cutAfter(left, width)
			rest = cutAfter(right, width)
			tail = mergeOnto(tail, left, right)
		}
	}
	return dummy.Next
}

// cutAfter detaches the first size nodes from the rest and returns the rest's head.
func cutAfter(head *ListNode, size int) *ListNode {
	for i := 0; i < size-1; i++ {
		if head == nil {
			return nil
		}
		head = head.Next
	}
	if head == nil {
		return nil
	}
	rest := head.Next
	head.Next = nil
	return rest
}

// mergeOnto appends the merge of two sorted runs after tail and returns the new tail.
func mergeOnto(tail, left, right *ListNode) *ListNode {
	for left != nil && right != nil {
		if left.Val <= right.Val {
			tail.Next, left = left, left.Next
		} else {
			tail.Next, right = right, right.Next
		}
		tail = tail.Next
	}
	if left != nil {
		tail.Next = left
	} else {
		tail.Next = right
	}
	for tail.Next != nil {
		tail = tail.Next
	}
	return tail
}
