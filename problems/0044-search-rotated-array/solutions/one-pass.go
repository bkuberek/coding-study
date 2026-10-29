package search_rotated_array

func search(nums []int, target int) int {
	low, high := 0, len(nums)-1
	for low <= high {
		middle := low + (high-low)/2
		if nums[middle] == target {
			return middle
		}
		if nums[low] <= nums[middle] {
			// nums[low..middle] is sorted.
			if nums[low] <= target && target < nums[middle] {
				high = middle - 1
			} else {
				low = middle + 1
			}
		} else {
			// nums[middle..high] is sorted.
			if nums[middle] < target && target <= nums[high] {
				low = middle + 1
			} else {
				high = middle - 1
			}
		}
	}
	return -1
}
