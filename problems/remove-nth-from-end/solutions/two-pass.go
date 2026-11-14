package remove_nth_from_end

import "cstudy/support"

type ListNode = support.ListNode

func removeNthFromEnd(head *ListNode, n int) *ListNode {
	length := 0
	for node := head; node != nil; node = node.Next {
		length++
	}
	// The dummy node is the predecessor of the head, so removing the head is not special.
	dummy := &ListNode{Next: head}
	before := dummy
	for i := 0; i < length-n; i++ {
		before = before.Next
	}
	before.Next = before.Next.Next
	return dummy.Next
}
