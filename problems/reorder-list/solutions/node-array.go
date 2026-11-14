package reorder_list

import "cstudy/support"

type ListNode = support.ListNode

func reorderList(head *ListNode) {
	var nodes []*ListNode
	for node := head; node != nil; node = node.Next {
		nodes = append(nodes, node)
	}
	if len(nodes) == 0 {
		return
	}
	left, right := 0, len(nodes)-1
	// Alternate: front node -> back node -> next front node, until the indexes meet.
	for left < right {
		nodes[left].Next = nodes[right]
		left++
		if left == right {
			break
		}
		nodes[right].Next = nodes[left]
		right--
	}
	nodes[left].Next = nil
}
