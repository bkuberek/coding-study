package missing_number

func missingNumber(nums []int) int {
	// Start with n, then fold in every index and value; present numbers cancel in pairs.
	result := len(nums)
	for index, value := range nums {
		result ^= index ^ value
	}
	return result
}
