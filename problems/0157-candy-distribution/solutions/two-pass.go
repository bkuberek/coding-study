package candy_distribution

func candy(ratings []int) int {
	n := len(ratings)
	candies := make([]int, n)
	for i := range candies {
		candies[i] = 1
	}
	// Left to right: the fewest candies that respect every left neighbor.
	for i := 1; i < n; i++ {
		if ratings[i] > ratings[i-1] {
			candies[i] = candies[i-1] + 1
		}
	}
	// Right to left: also respect every right neighbor, without undoing the first pass.
	for i := n - 2; i >= 0; i-- {
		if ratings[i] > ratings[i+1] {
			candies[i] = max(candies[i], candies[i+1]+1)
		}
	}
	total := 0
	for _, count := range candies {
		total += count
	}
	return total
}
