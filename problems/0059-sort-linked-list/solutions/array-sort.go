package sort_linked_list

import (
	"slices"

	"cstudy/support"
)

type ListNode = support.ListNode

func sortList(head *ListNode) *ListNode {
	var values []int
	for node := head; node != nil; node = node.Next {
		values = append(values, node.Val)
	}
	slices.Sort(values)
	// Write the sorted values back into the same nodes, in list order.
	node := head
	for _, value := range values {
		node.Val = value
		node = node.Next
	}
	return head
}
