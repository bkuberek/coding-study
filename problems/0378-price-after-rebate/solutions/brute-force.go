package price_after_rebate

func pricesAfterRebate(prices []int) []int {
	paid := make([]int, len(prices))
	copy(paid, prices)
	for slot := range prices {
		for later := slot + 1; later < len(prices); later++ {
			if prices[later] <= prices[slot] {
				paid[slot] = prices[slot] - prices[later]
				break
			}
		}
	}
	return paid
}
