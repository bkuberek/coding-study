package best_time_to_buy_sell_stock

func maxProfit(prices []int) int {
	best := 0
	for buy := range prices {
		for sell := buy + 1; sell < len(prices); sell++ {
			best = max(best, prices[sell]-prices[buy])
		}
	}
	return best
}
