package climbing_stairs

func climbStairs(n int) int {
	// ways[step] counts the move sequences that end exactly on step.
	ways := make([]int, n+1)
	ways[0] = 1
	ways[1] = 1
	for step := 2; step <= n; step++ {
		ways[step] = ways[step-1] + ways[step-2]
	}
	return ways[n]
}
