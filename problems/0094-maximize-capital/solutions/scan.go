package maximize_capital

func findMaximizedCapital(k int, w int, profits []int, capital []int) int {
	used := make([]bool, len(profits))
	for range k {
		best := -1
		for index, profit := range profits {
			if !used[index] && capital[index] <= w && (best < 0 || profit > profits[best]) {
				best = index
			}
		}
		if best < 0 {
			break // nothing affordable now, and capital cannot grow any more
		}
		used[best] = true
		w += profits[best]
	}
	return w
}
