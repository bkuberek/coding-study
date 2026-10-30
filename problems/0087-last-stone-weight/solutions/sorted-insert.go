package last_stone_weight

import "slices"

func lastStoneWeight(stones []int) int {
	remaining := slices.Clone(stones)
	slices.Sort(remaining)
	for len(remaining) > 1 {
		heaviest, second := remaining[len(remaining)-1], remaining[len(remaining)-2]
		remaining = remaining[:len(remaining)-2]
		if heaviest != second {
			leftover := heaviest - second
			// Binary search finds the slot in O(log n); shifting the tail to open it is O(n).
			position, _ := slices.BinarySearch(remaining, leftover)
			remaining = slices.Insert(remaining, position, leftover)
		}
	}
	if len(remaining) == 0 {
		return 0
	}
	return remaining[0]
}
