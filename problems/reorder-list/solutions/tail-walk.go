package reorder_list

import "cstudy/support"

type ListNode = support.ListNode

func reorderList(head *ListNode) {
	current := head
	// Each round moves the current tail right after `current`; two or fewer nodes from
	// `current` onward are already in their final order.
	for current != nil && current.Next != nil && current.Next.Next != nil {
		beforeTail := current
		for beforeTail.Next.Next != nil {
			beforeTail = beforeTail.Next
		}
		tail := beforeTail.Next
		beforeTail.Next = nil
		tail.Next = current.Next
		current.Next = tail
		current = tail.Next
	}
}
