package search_rotated_array

func search(nums []int, target int) int {
	for index, value := range nums {
		if value == target {
			return index
		}
	}
	return -1
}
