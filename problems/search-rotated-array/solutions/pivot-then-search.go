package search_rotated_array

func search(nums []int, target int) int {
	pivot := indexOfMinimum(nums)
	last := len(nums) - 1
	if nums[pivot] <= target && target <= nums[last] {
		return binarySearch(nums, target, pivot, last)
	}
	return binarySearch(nums, target, 0, pivot-1)
}

func indexOfMinimum(nums []int) int {
	low, high := 0, len(nums)-1
	for low < high {
		middle := low + (high-low)/2
		if nums[middle] > nums[high] {
			low = middle + 1
		} else {
			high = middle
		}
	}
	return low
}

func binarySearch(nums []int, target, low, high int) int {
	for low <= high {
		middle := low + (high-low)/2
		switch {
		case nums[middle] == target:
			return middle
		case nums[middle] < target:
			low = middle + 1
		default:
			high = middle - 1
		}
	}
	return -1
}
