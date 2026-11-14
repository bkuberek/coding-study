package reorder_list

import "cstudy/support"

type ListNode = support.ListNode

func reorderList(head *ListNode) {
	if head == nil {
		return
	}
	// 1. Find the end of the front half: for n nodes, `slow` stops at node (n - 1) / 2.
	slow, fast := head, head
	for fast.Next != nil && fast.Next.Next != nil {
		slow = slow.Next
		fast = fast.Next.Next
	}
	// 2. Cut the list and reverse the back half.
	back := reverse(slow.Next)
	slow.Next = nil
	// 3. Interleave; the front half is never shorter than the back half.
	front := head
	for back != nil {
		frontNext, backNext := front.Next, back.Next
		front.Next = back
		back.Next = frontNext
		front, back = frontNext, backNext
	}
}

func reverse(head *ListNode) *ListNode {
	var previous *ListNode
	for current := head; current != nil; {
		following := current.Next
		current.Next = previous
		previous, current = current, following
	}
	return previous
}
