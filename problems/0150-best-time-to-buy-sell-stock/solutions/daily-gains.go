package best_time_to_buy_sell_stock

func maxProfit(prices []int) int {
	// A trade from day i to day j earns the sum of the daily changes between them, so the
	// answer is the best sum of a run of consecutive changes (Kadane), or 0.
	best, endingHere := 0, 0
	for day := 1; day < len(prices); day++ {
		endingHere = max(0, endingHere+prices[day]-prices[day-1])
		best = max(best, endingHere)
	}
	return best
}
