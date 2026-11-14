package conformance_no_alias

import "cstudy/support"

type ListNode = support.ListNode

func copyList(head *ListNode) *ListNode {
	return head
}
