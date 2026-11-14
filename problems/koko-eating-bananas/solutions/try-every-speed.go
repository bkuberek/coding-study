package koko_eating_bananas

func minEatingSpeed(piles []int, h int) int {
	speed := 1
	for hoursAt(piles, speed) > h {
		speed++
	}
	return speed
}

func hoursAt(piles []int, speed int) int {
	hours := 0
	for _, pile := range piles {
		hours += (pile + speed - 1) / speed // ceiling division
	}
	return hours
}
