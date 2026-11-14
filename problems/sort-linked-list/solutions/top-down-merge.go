package sort_linked_list

import "cstudy/support"

type ListNode = support.ListNode

func sortList(head *ListNode) *ListNode {
	if head == nil || head.Next == nil {
		return head
	}
	// Starting `fast` one node ahead makes `slow` stop at the end of the left half,
	// so a two-node list splits into one node and one node.
	slow, fast := head, head.Next
	for fast != nil && fast.Next != nil {
		slow = slow.Next
		fast = fast.Next.Next
	}
	right := slow.Next
	slow.Next = nil
	return merge(sortList(head), sortList(right))
}

func merge(left, right *ListNode) *ListNode {
	dummy := &ListNode{}
	tail := dummy
	for left != nil && right != nil {
		if left.Val <= right.Val {
			tail.Next, left = left, left.Next
		} else {
			tail.Next, right = right, right.Next
		}
		tail = tail.Next
	}
	if left != nil {
		tail.Next = left
	} else {
		tail.Next = right
	}
	return dummy.Next
}
