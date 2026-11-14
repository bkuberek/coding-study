package climbing_stairs

func climbStairs(n int) int {
	// Before each iteration: twoBelow and oneBelow count the ways to reach the two
	// steps just below the one being computed.
	twoBelow, oneBelow := 1, 1
	for step := 2; step <= n; step++ {
		twoBelow, oneBelow = oneBelow, oneBelow+twoBelow
	}
	return oneBelow
}
