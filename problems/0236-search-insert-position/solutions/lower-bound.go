package search_insert_position

func searchInsert(nums []int, target int) int {
	low, high := 0, len(nums) // the answer lies in [low, high]
	for low < high {
		middle := low + (high-low)/2
		if nums[middle] < target {
			low = middle + 1
		} else {
			high = middle
		}
	}
	return low
}
