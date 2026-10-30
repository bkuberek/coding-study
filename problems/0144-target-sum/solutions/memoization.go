package target_sum

func findTargetSumWays(nums []int, target int) int {
	total := 0
	for _, value := range nums {
		total += value
	}
	// ways[index][running+total] caches the count from that state; -1 is unknown.
	ways := make([][]int, len(nums))
	for index := range ways {
		ways[index] = make([]int, 2*total+1)
		for offset := range ways[index] {
			ways[index][offset] = -1
		}
	}
	var count func(index, running int) int
	count = func(index, running int) int {
		if index == len(nums) {
			if running == target {
				return 1
			}
			return 0
		}
		offset := running + total
		if ways[index][offset] < 0 {
			ways[index][offset] = count(index+1, running+nums[index]) + count(index+1, running-nums[index])
		}
		return ways[index][offset]
	}
	return count(0, 0)
}
