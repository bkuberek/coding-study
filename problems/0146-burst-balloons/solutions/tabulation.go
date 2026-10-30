package burst_balloons

func maxCoins(nums []int) int {
	values := make([]int, 0, len(nums)+2)
	values = append(values, 1)
	values = append(values, nums...)
	values = append(values, 1)
	size := len(values)
	// best[left][right]: most coins from bursting everything strictly between left and right.
	best := make([][]int, size)
	for left := range best {
		best[left] = make([]int, size)
	}
	// An interval only depends on shorter ones, so fill by increasing gap right - left.
	for gap := 2; gap < size; gap++ {
		for left := 0; left+gap < size; left++ {
			right := left + gap
			outer := values[left] * values[right]
			row := best[left]
			top := 0
			for last := left + 1; last < right; last++ {
				top = max(top, row[last]+outer*values[last]+best[last][right])
			}
			row[right] = top
		}
	}
	return best[0][size-1]
}
