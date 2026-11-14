package price_after_rebate

func pricesAfterRebate(prices []int) []int {
	paid := make([]int, len(prices))
	copy(paid, prices)
	// Slots still waiting for a rebate; their prices rise strictly from bottom to top.
	var waiting []int
	for slot, price := range prices {
		for len(waiting) > 0 && prices[waiting[len(waiting)-1]] >= price {
			earlier := waiting[len(waiting)-1]
			waiting = waiting[:len(waiting)-1]
			paid[earlier] = prices[earlier] - price
		}
		waiting = append(waiting, slot)
	}
	return paid
}
