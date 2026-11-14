package linked_list_cycle

import "cstudy/support"

type ListNode = support.ListNode

func hasCycle(head *ListNode) bool {
	slow, fast := head, head
	// The fast pointer reaches the end first when there is no loop; inside a loop it gains
	// one node per step on the slow pointer and must land on it.
	for fast != nil && fast.Next != nil {
		slow = slow.Next
		fast = fast.Next.Next
		if slow == fast {
			return true
		}
	}
	return false
}
