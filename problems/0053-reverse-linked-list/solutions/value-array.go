package reverse_linked_list

import "cstudy/support"

type ListNode = support.ListNode

func reverseList(head *ListNode) *ListNode {
	var values []int
	for node := head; node != nil; node = node.Next {
		values = append(values, node.Val)
	}
	// Second pass: the same nodes, in the same order, receive the values from the back.
	index := len(values) - 1
	for node := head; node != nil; node = node.Next {
		node.Val = values[index]
		index--
	}
	return head
}
