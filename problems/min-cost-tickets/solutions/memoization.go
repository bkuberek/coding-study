package min_cost_tickets

import "math"

var durations = [3]int{1, 7, 30}

func mincostTickets(days []int, costs []int) int {
	// A pass bought for days[index] covers through days[index] + duration - 1; this is
	// the first trip it leaves uncovered.
	firstUncovered := func(index, duration int) int {
		following := index
		for following < len(days) && days[following] < days[index]+duration {
			following++
		}
		return following
	}

	// memo[index] is the cheapest cost of covering days[index:], or -1 while unknown.
	memo := make([]int, len(days))
	for i := range memo {
		memo[i] = -1
	}
	var cheapestFrom func(index int) int
	cheapestFrom = func(index int) int {
		if index == len(days) {
			return 0
		}
		if memo[index] == -1 {
			cheapest := math.MaxInt
			for pass, duration := range durations {
				cheapest = min(cheapest, costs[pass]+cheapestFrom(firstUncovered(index, duration)))
			}
			memo[index] = cheapest
		}
		return memo[index]
	}
	return cheapestFrom(0)
}
