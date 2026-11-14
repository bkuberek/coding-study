package coin_change

func coinChange(coins []int, amount int) int {
	// fewest[x] is the fewest coins that pay x exactly; amount + 1 means "cannot be paid",
	// since any real answer uses at most amount coins.
	unreachable := amount + 1
	fewest := make([]int, amount+1)
	for x := 1; x <= amount; x++ {
		fewest[x] = unreachable
	}
	for x := 1; x <= amount; x++ {
		for _, coin := range coins {
			if coin <= x && fewest[x-coin]+1 < fewest[x] {
				fewest[x] = fewest[x-coin] + 1
			}
		}
	}
	if fewest[amount] == unreachable {
		return -1
	}
	return fewest[amount]
}
