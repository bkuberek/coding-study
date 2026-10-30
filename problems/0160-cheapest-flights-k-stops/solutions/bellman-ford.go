package cheapest_flights_k_stops

import (
	"math"
	"slices"
)

const unreached = math.MaxInt

func findCheapestPrice(n int, flights [][]int, src int, dst int, k int) int {
	// price[c] is the cheapest known price to reach c with at most `round` flights.
	price := make([]int, n)
	for city := range price {
		price[city] = unreached
	}
	price[src] = 0
	for round := 0; round <= k; round++ {
		// Read from the previous round only, so one round never chains two flights.
		previous := slices.Clone(price)
		changed := false
		for _, flight := range flights {
			start, end, cost := flight[0], flight[1], flight[2]
			if previous[start] != unreached && previous[start]+cost < price[end] {
				price[end] = previous[start] + cost
				changed = true
			}
		}
		if !changed {
			break
		}
	}
	if price[dst] == unreached {
		return -1
	}
	return price[dst]
}
