package coin_change_ways

func change(amount int, coins []int) int {
	// ways[i][total] is the number of combinations for `total` using only coins[:i].
	ways := make([][]int, len(coins)+1)
	for i := range ways {
		ways[i] = make([]int, amount+1)
	}
	ways[0][0] = 1
	for i := 1; i <= len(coins); i++ {
		coin := coins[i-1]
		for total := 0; total <= amount; total++ {
			// Combinations without this coin, plus those that use it at least once.
			ways[i][total] = ways[i-1][total]
			if total >= coin {
				ways[i][total] += ways[i][total-coin]
			}
		}
	}
	return ways[len(coins)][amount]
}
