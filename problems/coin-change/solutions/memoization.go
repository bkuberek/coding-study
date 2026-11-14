package coin_change

const (
	notComputed = -1
	infinity    = 1 << 30 // larger than any real answer, small enough that 1 + infinity cannot overflow
)

func coinChange(coins []int, amount int) int {
	memo := make([]int, amount+1)
	for remaining := range memo {
		memo[remaining] = notComputed
	}

	// fewest returns the fewest coins that pay remaining exactly; infinity when it cannot be paid.
	var fewest func(remaining int) int
	fewest = func(remaining int) int {
		if remaining == 0 {
			return 0
		}
		if memo[remaining] == notComputed {
			best := infinity
			for _, coin := range coins {
				if coin <= remaining {
					best = min(best, 1+fewest(remaining-coin))
				}
			}
			memo[remaining] = best
		}
		return memo[remaining]
	}

	answer := fewest(amount)
	if answer >= infinity {
		return -1
	}
	return answer
}
