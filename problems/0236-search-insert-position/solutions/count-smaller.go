package search_insert_position

func searchInsert(nums []int, target int) int {
	// In a sorted array, target belongs right after every smaller value.
	smaller := 0
	for _, value := range nums {
		if value < target {
			smaller++
		}
	}
	return smaller
}
