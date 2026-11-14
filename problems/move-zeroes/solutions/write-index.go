package move_zeroes

func moveZeroes(nums []int) {
	write := 0
	for _, value := range nums {
		if value != 0 {
			nums[write] = value
			write++
		}
	}
	clear(nums[write:])
}
