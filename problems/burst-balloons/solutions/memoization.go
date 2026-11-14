package burst_balloons

func maxCoins(nums []int) int {
	// Pad with the virtual balloons of value 1 at both ends.
	values := make([]int, 0, len(nums)+2)
	values = append(values, 1)
	values = append(values, nums...)
	values = append(values, 1)
	// best[left][right] caches the most coins from bursting every balloon strictly between
	// left and right, while those two are still standing; -1 is unknown.
	best := make([][]int, len(values))
	for left := range best {
		best[left] = make([]int, len(values))
		for right := range best[left] {
			best[left][right] = -1
		}
	}
	var solve func(left, right int) int
	solve = func(left, right int) int {
		if right-left < 2 {
			return 0
		}
		if best[left][right] < 0 {
			// Choose the balloon `last` that is burst last between them: its neighbors are
			// then exactly left and right, and the two sides are independent.
			top := 0
			for last := left + 1; last < right; last++ {
				top = max(top, solve(left, last)+values[left]*values[last]*values[right]+solve(last, right))
			}
			best[left][right] = top
		}
		return best[left][right]
	}
	return solve(0, len(values)-1)
}
