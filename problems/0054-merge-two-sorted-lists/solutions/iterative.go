package merge_two_sorted_lists

import "cstudy/support"

type ListNode = support.ListNode

func mergeTwoLists(list1 *ListNode, list2 *ListNode) *ListNode {
	// The dummy node gives the merged list a fixed place to start, so the first splice
	// needs no special case.
	dummy := &ListNode{}
	tail := dummy
	for list1 != nil && list2 != nil {
		if list1.Val <= list2.Val {
			tail.Next, list1 = list1, list1.Next
		} else {
			tail.Next, list2 = list2, list2.Next
		}
		tail = tail.Next
	}
	// At most one list has nodes left, and they are already sorted: link them as a block.
	if list1 != nil {
		tail.Next = list1
	} else {
		tail.Next = list2
	}
	return dummy.Next
}
