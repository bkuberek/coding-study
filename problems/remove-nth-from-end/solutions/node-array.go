package remove_nth_from_end

import "cstudy/support"

type ListNode = support.ListNode

func removeNthFromEnd(head *ListNode, n int) *ListNode {
	var nodes []*ListNode
	for node := head; node != nil; node = node.Next {
		nodes = append(nodes, node)
	}
	target := len(nodes) - n
	if target == 0 {
		return nodes[0].Next
	}
	nodes[target-1].Next = nodes[target].Next
	return head
}
