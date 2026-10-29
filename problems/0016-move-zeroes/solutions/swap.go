package move_zeroes

func moveZeroes(nums []int) {
	write := 0
	for read := range nums {
		if nums[read] != 0 {
			nums[write], nums[read] = nums[read], nums[write]
			write++
		}
	}
}
