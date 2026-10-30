package house_robber

const notComputed = -1

func rob(nums []int) int {
	memo := make([]int, len(nums))
	for house := range memo {
		memo[house] = notComputed
	}

	var bestFrom func(house int) int
	bestFrom = func(house int) int {
		// The most cash obtainable from houses house, house + 1, ..., the last one.
		if house >= len(nums) {
			return 0
		}
		if memo[house] == notComputed {
			skip := bestFrom(house + 1)
			take := nums[house] + bestFrom(house+2)
			memo[house] = max(skip, take)
		}
		return memo[house]
	}

	return bestFrom(0)
}
