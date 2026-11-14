package min_size_subarray_sum

func minSubArrayLen(target int, nums []int) int {
	best, total, left := 0, 0, 0
	for right, value := range nums {
		total += value
		for total >= target {
			if best == 0 || right-left+1 < best {
				best = right - left + 1
			}
			total -= nums[left]
			left++
		}
	}
	return best
}
