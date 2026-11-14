package merge_two_sorted_lists

import (
	"slices"

	"cstudy/support"
)

type ListNode = support.ListNode

func mergeTwoLists(list1 *ListNode, list2 *ListNode) *ListNode {
	var values []int
	for _, node := range []*ListNode{list1, list2} {
		for ; node != nil; node = node.Next {
			values = append(values, node.Val)
		}
	}
	slices.Sort(values)
	dummy := &ListNode{}
	tail := dummy
	for _, value := range values {
		tail.Next = &ListNode{Val: value}
		tail = tail.Next
	}
	return dummy.Next
}
