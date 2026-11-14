package stock_with_cooldown

func maxProfit(prices []int) int {
	// memo[holding][day] is the most profit from day on, or unknown while it is -1.
	var memo [2][]int
	for holding := range memo {
		memo[holding] = make([]int, len(prices))
		for day := range memo[holding] {
			memo[holding][day] = -1
		}
	}
	var best func(day, holding int) int
	best = func(day, holding int) int {
		if day >= len(prices) {
			return 0
		}
		if memo[holding][day] == -1 {
			wait := best(day+1, holding)
			var act int
			if holding == 1 {
				// Selling today forces tomorrow to be a cooldown day, so resume on day + 2.
				act = prices[day] + best(day+2, 0)
			} else {
				act = -prices[day] + best(day+1, 1)
			}
			memo[holding][day] = max(wait, act)
		}
		return memo[holding][day]
	}
	return best(0, 0)
}
