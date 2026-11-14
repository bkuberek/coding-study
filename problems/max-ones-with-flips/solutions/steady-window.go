package max_ones_with_flips

func longestOnes(nums []int, k int) int {
	left, flipsLeft := 0, k
	for _, value := range nums {
		if value == 0 {
			flipsLeft--
		}
		if flipsLeft < 0 {
			if nums[left] == 0 {
				flipsLeft++
			}
			left++
		}
	}
	return len(nums) - left
}
