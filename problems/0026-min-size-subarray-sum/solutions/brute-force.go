package min_size_subarray_sum

func minSubArrayLen(target int, nums []int) int {
	best := 0
	for start := range nums {
		total := 0
		for end := start; end < len(nums); end++ {
			total += nums[end]
			if total >= target {
				if best == 0 || end-start+1 < best {
					best = end - start + 1
				}
				break
			}
		}
	}
	return best
}
