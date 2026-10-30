package missing_number

func missingNumber(nums []int) int {
	n := len(nums)
	// n * (n + 1) / 2 reaches 5 * 10^9 for n = 10^5, which a 64-bit int holds.
	difference := n * (n + 1) / 2
	for _, value := range nums {
		difference -= value
	}
	return difference
}
