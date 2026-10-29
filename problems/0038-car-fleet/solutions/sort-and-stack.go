package car_fleet

import (
	"cmp"
	"slices"
)

func carFleet(target int, position []int, speed []int) int {
	cars := make([]int, len(position))
	for car := range cars {
		cars[car] = car
	}
	slices.SortFunc(cars, func(a, b int) int { return cmp.Compare(position[a], position[b]) })
	// Fleets formed so far, from the farthest back (bottom) to the closest to the target (top);
	// their arrival times strictly decrease from bottom to top.
	var fleets []float64
	for _, car := range cars {
		arrival := float64(target-position[car]) / float64(speed[car])
		// Every fleet behind this car that would arrive no later catches up with it.
		for len(fleets) > 0 && fleets[len(fleets)-1] <= arrival {
			fleets = fleets[:len(fleets)-1]
		}
		fleets = append(fleets, arrival)
	}
	return len(fleets)
}
