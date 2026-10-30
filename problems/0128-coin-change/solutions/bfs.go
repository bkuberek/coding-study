package coin_change

func coinChange(coins []int, amount int) int {
	// Remainders are nodes; paying one coin is an edge. The first level that reaches 0 is
	// the fewest number of coins.
	seen := make([]bool, amount+1)
	seen[amount] = true
	level := []int{amount}
	coinsUsed := 0
	for len(level) > 0 {
		if seen[0] {
			return coinsUsed
		}
		var nextLevel []int
		for _, remaining := range level {
			for _, coin := range coins {
				rest := remaining - coin
				if rest >= 0 && !seen[rest] {
					seen[rest] = true
					nextLevel = append(nextLevel, rest)
				}
			}
		}
		level = nextLevel
		coinsUsed++
	}
	return -1
}
