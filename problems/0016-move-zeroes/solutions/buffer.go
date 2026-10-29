package move_zeroes

func moveZeroes(nums []int) {
	nonZero := make([]int, 0, len(nums))
	for _, value := range nums {
		if value != 0 {
			nonZero = append(nonZero, value)
		}
	}
	copy(nums, nonZero)
	clear(nums[len(nonZero):])
}
