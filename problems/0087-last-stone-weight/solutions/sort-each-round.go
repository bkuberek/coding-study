package last_stone_weight

import "slices"

func lastStoneWeight(stones []int) int {
	remaining := slices.Clone(stones)
	for len(remaining) > 1 {
		slices.Sort(remaining)
		heaviest, second := remaining[len(remaining)-1], remaining[len(remaining)-2]
		remaining = remaining[:len(remaining)-2]
		if heaviest != second {
			remaining = append(remaining, heaviest-second)
		}
	}
	if len(remaining) == 0 {
		return 0
	}
	return remaining[0]
}
