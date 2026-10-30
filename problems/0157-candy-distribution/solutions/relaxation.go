package candy_distribution

func candy(ratings []int) int {
	n := len(ratings)
	candies := make([]int, n)
	for i := range candies {
		candies[i] = 1
	}
	for changed := true; changed; {
		// Raise any child who does not have more than a lower-rated neighbor; repeat until no
		// rule is violated. Counts only grow, and each raise is the least that fixes it.
		changed = false
		for i := 0; i < n; i++ {
			if i > 0 && ratings[i] > ratings[i-1] && candies[i] <= candies[i-1] {
				candies[i] = candies[i-1] + 1
				changed = true
			}
			if i < n-1 && ratings[i] > ratings[i+1] && candies[i] <= candies[i+1] {
				candies[i] = candies[i+1] + 1
				changed = true
			}
		}
	}
	total := 0
	for _, count := range candies {
		total += count
	}
	return total
}
