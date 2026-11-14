package max_ones_with_flips

func longestOnes(nums []int, k int) int {
	left, zeros, best := 0, 0, 0
	for right, value := range nums {
		if value == 0 {
			zeros++
		}
		for zeros > k {
			if nums[left] == 0 {
				zeros--
			}
			left++
		}
		best = max(best, right-left+1)
	}
	return best
}
