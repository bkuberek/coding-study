package first_missing_positive

func firstMissingPositive(nums []int) int {
	present := make(map[int]bool, len(nums))
	for _, value := range nums {
		present[value] = true
	}
	// The answer is at most len(nums) + 1, so this loop runs at most n + 1 times.
	candidate := 1
	for present[candidate] {
		candidate++
	}
	return candidate
}
