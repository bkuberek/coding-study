package reverse_nodes_in_k_group

import "cstudy/support"

type ListNode = support.ListNode

func reverseKGroup(head *ListNode, k int) *ListNode {
	dummy := &ListNode{Next: head}
	before := dummy // the node just before the next group
	for {
		last := before
		for i := 0; i < k; i++ {
			last = last.Next
			if last == nil {
				return dummy.Next // fewer than k nodes remain: leave them as they are
			}
		}
		after := last.Next
		// Reverse the group; its first node ends up last, pointing at `after`.
		first := before.Next
		previous, current := after, first
		for current != after {
			following := current.Next
			current.Next = previous
			previous, current = current, following
		}
		before.Next = last
		before = first
	}
}
