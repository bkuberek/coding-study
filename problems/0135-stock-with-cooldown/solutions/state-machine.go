package stock_with_cooldown

func maxProfit(prices []int) int {
	// The three end-of-day states of the previous day: holding a share, just sold, resting.
	hold, sold, rest := -prices[0], 0, 0
	for _, price := range prices[1:] {
		hold, sold, rest = max(hold, rest-price), hold+price, max(rest, sold)
	}
	return max(sold, rest)
}
