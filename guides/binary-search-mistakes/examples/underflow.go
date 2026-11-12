// Unsigned numbers cannot go below zero: a subtraction whose true result is negative wraps around
// to a huge value instead. Go does this silently, so the bug shows up as a wrong answer, not a crash.
package main

import (
	"fmt"
	"sort"
)

// carelessGap assumes station <= x, which is true on one side of x only.
func carelessGap(x, station uint64) uint64 {
	return x - station
}

// gap subtracts the smaller value from the larger one, so it never goes below zero.
func gap(x, station uint64) uint64 {
	if station > x {
		return station - x
	}
	return x - station
}

func main() {
	stations := []uint64{120, 340, 560, 910} // kilometre posts along a railway, sorted
	x := uint64(500)

	// The first station at or after kilometre 500; its neighbour before it is the other candidate.
	i := sort.Search(len(stations), func(i int) bool { return stations[i] >= x })
	before, after := stations[i-1], stations[i]
	fmt.Println("lower bound of 500:", i, "| neighbours:", before, "and", after)

	fmt.Println("careless gaps:", carelessGap(x, before), "and", carelessGap(x, after))
	fmt.Println("gaps:         ", gap(x, before), "and", gap(x, after))

	nearest := func(distance func(x, station uint64) uint64) uint64 {
		if distance(x, before) <= distance(x, after) {
			return before
		}
		return after
	}
	fmt.Println("nearest, careless:", nearest(carelessGap), "| nearest:", nearest(gap))
}
