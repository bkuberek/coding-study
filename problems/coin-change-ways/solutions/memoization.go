package coin_change_ways

func change(amount int, coins []int) int {
	// ways[i][total] caches the combinations for `total` using coins[i:]; -1 is unknown.
	ways := make([][]int, len(coins))
	for i := range ways {
		ways[i] = make([]int, amount+1)
		for total := range ways[i] {
			ways[i][total] = -1
		}
	}
	var count func(i, total int) int
	count = func(i, total int) int {
		if total == 0 {
			return 1
		}
		if i == len(coins) {
			return 0
		}
		if ways[i][total] < 0 {
			// Either no coin of value coins[i] is used, or at least one is.
			skip := count(i+1, total)
			use := 0
			if coins[i] <= total {
				use = count(i, total-coins[i])
			}
			ways[i][total] = skip + use
		}
		return ways[i][total]
	}
	return count(0, amount)
}
