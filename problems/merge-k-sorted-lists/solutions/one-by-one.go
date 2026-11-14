package merge_k_sorted_lists

import "cstudy/support"

type ListNode = support.ListNode

func mergeKLists(lists []*ListNode) *ListNode {
	var merged *ListNode
	for _, head := range lists {
		merged = merge(merged, head)
	}
	return merged
}

func merge(left, right *ListNode) *ListNode {
	dummy := &ListNode{}
	tail := dummy
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
	return dummy.Next
}
