package min_in_rotated_array

func findMin(nums []int) int {
	smallest := nums[0]
	for _, value := range nums {
		if value < smallest {
			smallest = value
		}
	}
	return smallest
}
