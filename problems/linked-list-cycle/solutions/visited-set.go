package linked_list_cycle

import "cstudy/support"

type ListNode = support.ListNode

func hasCycle(head *ListNode) bool {
	// Pointers compare by address, so equal values in different nodes stay distinct.
	visited := make(map[*ListNode]struct{})
	for node := head; node != nil; node = node.Next {
		if _, seen := visited[node]; seen {
			return true
		}
		visited[node] = struct{}{}
	}
	return false
}
