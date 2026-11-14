package target_sum

func findTargetSumWays(nums []int, target int) int {
	var count func(index, total int) int
	count = func(index, total int) int {
		if index == len(nums) {
			if total == target {
				return 1
			}
			return 0
		}
		// Give nums[index] a plus sign, then a minus sign.
		return count(index+1, total+nums[index]) + count(index+1, total-nums[index])
	}
	return count(0, 0)
}
