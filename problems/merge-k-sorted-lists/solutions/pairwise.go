package merge_k_sorted_lists

import (
	"slices"

	"cstudy/support"
)

type ListNode = support.ListNode

func mergeKLists(lists []*ListNode) *ListNode {
	if len(lists) == 0 {
		return nil
	}
	// Each round merges neighbours (0 with 1, 2 with 3, ...), halving the number of lists;
	// every node takes part in one merge per round, and there are ceil(log2 k) rounds.
	heads := slices.Clone(lists)
	for len(heads) > 1 {
		merged := make([]*ListNode, 0, (len(heads)+1)/2)
		for index := 0; index < len(heads); index += 2 {
			var right *ListNode
			if index+1 < len(heads) {
				right = heads[index+1]
			}
			merged = append(merged, merge(heads[index], right))
		}
		heads = merged
	}
	return heads[0]
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
