package target_sum

func findTargetSumWays(nums []int, target int) int {
	total := 0
	for _, value := range nums {
		total += value
	}
	if target > total || target < -total {
		return 0
	}
	// ways[i][running+total] counts the sign assignments of nums[:i] with that running total.
	ways := make([][]int, len(nums)+1)
	for i := range ways {
		ways[i] = make([]int, 2*total+1)
	}
	ways[0][total] = 1
	for i, value := range nums {
		for offset, count := range ways[i] {
			if count > 0 {
				ways[i+1][offset+value] += count
				ways[i+1][offset-value] += count
			}
		}
	}
	return ways[len(nums)][target+total]
}
