package single_number

func singleNumber(nums []int) int {
	// Pairs cancel (a ^ a == 0) in any order, so only the single value is left.
	result := 0
	for _, value := range nums {
		result ^= value
	}
	return result
}
