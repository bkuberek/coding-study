package partition_equal_subset_sum

func canPartition(nums []int) bool {
	total := 0
	for _, value := range nums {
		total += value
	}
	if total%2 == 1 {
		return false
	}
	target := total / 2
	// reach[i][s] is true when some of the first i elements add up to exactly s.
	reach := make([][]bool, len(nums)+1)
	for i := range reach {
		reach[i] = make([]bool, target+1)
	}
	reach[0][0] = true
	for i, value := range nums {
		previous, current := reach[i], reach[i+1]
		for s := 0; s <= target; s++ {
			current[s] = previous[s] || (s >= value && previous[s-value])
		}
	}
	return reach[len(nums)][target]
}
