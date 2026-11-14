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
	// reachable[s] is true when some of the elements seen so far add up to exactly s.
	reachable := make([]bool, target+1)
	reachable[0] = true
	for _, value := range nums {
		// Right to left, so reachable[s-value] still describes the elements before value.
		for s := target; s >= value; s-- {
			if reachable[s-value] {
				reachable[s] = true
			}
		}
		if reachable[target] {
			return true
		}
	}
	return reachable[target]
}
