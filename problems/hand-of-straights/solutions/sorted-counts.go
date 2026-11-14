package hand_of_straights

import (
	"maps"
	"slices"
)

func isNStraightHand(hand []int, groupSize int) bool {
	if len(hand)%groupSize != 0 {
		return false
	}
	counts := make(map[int]int, len(hand))
	for _, card := range hand {
		counts[card]++
	}
	for _, value := range slices.Sorted(maps.Keys(counts)) {
		starting := counts[value]
		if starting == 0 {
			continue
		}
		// Every card left at the smallest remaining value starts its own straight.
		for following := value; following < value+groupSize; following++ {
			if counts[following] < starting {
				return false
			}
			counts[following] -= starting
		}
	}
	return true
}
