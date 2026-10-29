package koko_eating_bananas

import "slices"

func minEatingSpeed(piles []int, h int) int {
	// Hours never increase with speed: find the first speed in [1, max(piles)] that fits.
	low, high := 1, slices.Max(piles)
	for low < high {
		speed := low + (high-low)/2
		if hoursAt(piles, speed) <= h {
			high = speed
		} else {
			low = speed + 1
		}
	}
	return low
}

func hoursAt(piles []int, speed int) int {
	hours := 0
	for _, pile := range piles {
		hours += (pile + speed - 1) / speed // ceiling division
	}
	return hours
}
