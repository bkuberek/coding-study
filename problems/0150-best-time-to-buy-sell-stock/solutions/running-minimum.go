package best_time_to_buy_sell_stock

func maxProfit(prices []int) int {
	cheapest := prices[0]
	best := 0
	for _, price := range prices {
		// Selling today, the best purchase is the cheapest earlier day (or today: profit 0).
		best = max(best, price-cheapest)
		cheapest = min(cheapest, price)
	}
	return best
}
