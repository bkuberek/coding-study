package first_last_position

func searchRange(nums []int, target int) []int {
	low, high := 0, len(nums)-1
	for low <= high {
		middle := low + (high-low)/2
		switch {
		case nums[middle] == target:
			first, last := middle, middle
			for first > 0 && nums[first-1] == target {
				first--
			}
			for last < len(nums)-1 && nums[last+1] == target {
				last++
			}
			return []int{first, last}
		case nums[middle] < target:
			low = middle + 1
		default:
			high = middle - 1
		}
	}
	return []int{-1, -1}
}
