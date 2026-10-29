package reverse_linked_list

import "cstudy/support"

type ListNode = support.ListNode

func reverseList(head *ListNode) *ListNode {
	if head == nil || head.Next == nil {
		return head
	}
	newHead := reverseList(head.Next)
	// head.Next is now the tail of the reversed rest; head goes after it.
	head.Next.Next = head
	head.Next = nil
	return newHead
}
