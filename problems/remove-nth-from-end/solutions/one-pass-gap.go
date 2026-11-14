package remove_nth_from_end

import "cstudy/support"

type ListNode = support.ListNode

func removeNthFromEnd(head *ListNode, n int) *ListNode {
	dummy := &ListNode{Next: head}
	// `lead` starts n + 1 nodes ahead of `trail`; when `lead` falls off the end,
	// `trail` sits just before the node to remove.
	lead := dummy
	for i := 0; i < n+1; i++ {
		lead = lead.Next
	}
	trail := dummy
	for lead != nil {
		lead = lead.Next
		trail = trail.Next
	}
	trail.Next = trail.Next.Next
	return dummy.Next
}
