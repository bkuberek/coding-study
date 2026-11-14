package coin_change_ways

func change(amount int, coins []int) int {
	// After processing a prefix of the coins, ways[total] counts the combinations for `total`
	// that use only those coins.
	ways := make([]int, amount+1)
	ways[0] = 1
	for _, coin := range coins {
		// Increasing totals: ways[total-coin] already allows this coin, so it can repeat.
		for total := coin; total <= amount; total++ {
			ways[total] += ways[total-coin]
		}
	}
	return ways[amount]
}
