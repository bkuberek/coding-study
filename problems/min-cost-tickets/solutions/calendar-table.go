package min_cost_tickets

func mincostTickets(days []int, costs []int) int {
	lastDay := days[len(days)-1]
	travel := make([]bool, lastDay+1)
	for _, day := range days {
		travel[day] = true
	}
	// cost[d] is the cheapest way to cover every trip on calendar days 1..d.
	cost := make([]int, lastDay+1)
	for d := 1; d <= lastDay; d++ {
		if !travel[d] {
			cost[d] = cost[d-1]
			continue
		}
		cost[d] = min(
			cost[d-1]+costs[0],
			cost[max(0, d-7)]+costs[1],
			cost[max(0, d-30)]+costs[2],
		)
	}
	return cost[lastDay]
}
