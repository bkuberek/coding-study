package climbing_stairs

func climbStairs(n int) int {
	memo := make([]int, n+1) // 0 means "not computed yet": every step has at least one way

	var ways func(step int) int
	ways = func(step int) int {
		// One way to stand on the ground (step 0), one way to reach step 1.
		if step <= 1 {
			return 1
		}
		if memo[step] == 0 {
			memo[step] = ways(step-1) + ways(step-2)
		}
		return memo[step]
	}

	return ways(n)
}
