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
	// Straights started but not yet complete; each needs the current value.
	openCount := 0
	// Straights opened at each of the last groupSize values.
	var opened []int
	previous := 0
	for _, value := range slices.Sorted(maps.Keys(counts)) {
		if openCount > 0 && value != previous+1 {
			return false // an open straight needs previous + 1, which is missing
		}
		if counts[value] < openCount {
			return false
		}
		started := counts[value] - openCount
		opened = append(opened, started)
		openCount += started
		if len(opened) == groupSize {
			// The straights opened groupSize values ago end with this value.
			openCount -= opened[0]
			opened = opened[1:]
		}
		previous = value
	}
	return openCount == 0
}
