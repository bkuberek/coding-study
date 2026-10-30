package hand_of_straights

import "slices"

func isNStraightHand(hand []int, groupSize int) bool {
	if len(hand)%groupSize != 0 {
		return false
	}
	cards := slices.Clone(hand)
	slices.Sort(cards)
	for len(cards) > 0 {
		// The smallest card must start a straight; remove that straight card by card.
		smallest := cards[0]
		cards = cards[1:]
		for value := smallest + 1; value < smallest+groupSize; value++ {
			index := slices.Index(cards, value)
			if index < 0 {
				return false
			}
			cards = slices.Delete(cards, index, index+1)
		}
	}
	return true
}
