package reverse_nodes_in_k_group

import (
	"slices"

	"cstudy/support"
)

type ListNode = support.ListNode

func reverseKGroup(head *ListNode, k int) *ListNode {
	var values []int
	for node := head; node != nil; node = node.Next {
		values = append(values, node.Val)
	}
	// Reverse every full chunk; a shorter chunk at the end keeps its order.
	for start := 0; start+k <= len(values); start += k {
		slices.Reverse(values[start : start+k])
	}
	node := head
	for _, value := range values {
		node.Val = value
		node = node.Next
	}
	return head
}
