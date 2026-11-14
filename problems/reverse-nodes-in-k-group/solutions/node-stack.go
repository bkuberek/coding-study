package reverse_nodes_in_k_group

import "cstudy/support"

type ListNode = support.ListNode

func reverseKGroup(head *ListNode, k int) *ListNode {
	dummy := &ListNode{}
	tail := dummy
	node := head
	stack := make([]*ListNode, 0, k)
	for {
		// Take up to k nodes; popping them off the stack yields the group reversed.
		stack = stack[:0]
		probe := node
		for probe != nil && len(stack) < k {
			stack = append(stack, probe)
			probe = probe.Next
		}
		if len(stack) < k {
			tail.Next = node // a short tail keeps its order
			return dummy.Next
		}
		for len(stack) > 0 {
			tail.Next = stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			tail = tail.Next
		}
		node = probe
	}
}
