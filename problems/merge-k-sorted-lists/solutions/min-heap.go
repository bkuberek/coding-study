package merge_k_sorted_lists

import (
	"container/heap"

	"cstudy/support"
)

type ListNode = support.ListNode

// nodeHeap is a min-heap of list heads ordered by value, for container/heap.
type nodeHeap []*ListNode

func (h nodeHeap) Len() int           { return len(h) }
func (h nodeHeap) Less(i, j int) bool { return h[i].Val < h[j].Val }
func (h nodeHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *nodeHeap) Push(x any)        { *h = append(*h, x.(*ListNode)) }
func (h *nodeHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func mergeKLists(lists []*ListNode) *ListNode {
	// The heap holds the current head of every non-empty list; no tie-break is needed
	// because Less compares plain values.
	heads := make(nodeHeap, 0, len(lists))
	for _, head := range lists {
		if head != nil {
			heads = append(heads, head)
		}
	}
	heap.Init(&heads)
	dummy := &ListNode{}
	tail := dummy
	for heads.Len() > 0 {
		node := heads[0]
		tail.Next = node
		tail = node
		if node.Next != nil {
			heads[0] = node.Next
			heap.Fix(&heads, 0)
		} else {
			heap.Pop(&heads)
		}
	}
	return dummy.Next
}
