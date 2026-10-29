package sort_linked_list

import "cstudy/support"

type ListNode = support.ListNode

func sortList(head *ListNode) *ListNode {
	dummy := &ListNode{} // head of the sorted prefix
	node := head
	for node != nil {
		following := node.Next
		// Find the last sorted node whose value is smaller, and insert after it.
		spot := dummy
		for spot.Next != nil && spot.Next.Val < node.Val {
			spot = spot.Next
		}
		node.Next = spot.Next
		spot.Next = node
		node = following
	}
	return dummy.Next
}
