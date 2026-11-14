package conformance_no_alias

import "cstudy/support"

type ListNode = support.ListNode

func copyList(head *ListNode) *ListNode {
	dummy := &ListNode{}
	tail := dummy
	for node := head; node != nil; node = node.Next {
		tail.Next = &ListNode{Val: node.Val}
		tail = tail.Next
	}
	return dummy.Next
}
