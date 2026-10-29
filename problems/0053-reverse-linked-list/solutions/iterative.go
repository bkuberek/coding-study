package reverse_linked_list

import "cstudy/support"

type ListNode = support.ListNode

func reverseList(head *ListNode) *ListNode {
	var previous *ListNode
	current := head
	for current != nil {
		// Save the rest of the list before the link that leads to it is redirected.
		following := current.Next
		current.Next = previous
		previous, current = current, following
	}
	return previous
}
