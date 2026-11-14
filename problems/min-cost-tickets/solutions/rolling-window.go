package min_cost_tickets

const window = 30

func mincostTickets(days []int, costs []int) int {
	// cost[d%window] holds the cheapest cover of days 1..d for the last 30 calendar days;
	// nothing older is ever read, because the longest pass lasts 30 days.
	var cost [window]int
	nextTrip := 0
	lastDay := days[len(days)-1]
	for d := 1; d <= lastDay; d++ {
		previous := cost[(d-1)%window]
		if d != days[nextTrip] {
			cost[d%window] = previous
			continue
		}
		nextTrip++
		weekAgo, monthAgo := 0, 0
		if d >= 7 {
			weekAgo = cost[(d-7)%window]
		}
		if d >= window {
			monthAgo = cost[d%window]
		}
		cost[d%window] = min(previous+costs[0], weekAgo+costs[1], monthAgo+costs[2])
	}
	return cost[lastDay%window]
}
