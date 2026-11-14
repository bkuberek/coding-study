package max_ones_with_flips

func longestOnes(nums []int, k int) int {
	best := 0
	for start := range nums {
		zeros := 0
		end := start
		for end < len(nums) {
			if nums[end] == 0 {
				if zeros == k {
					break
				}
				zeros++
			}
			end++
		}
		best = max(best, end-start)
	}
	return best
}
