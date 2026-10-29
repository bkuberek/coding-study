package first_last_position

func searchRange(nums []int, target int) []int {
	first, last := -1, -1
	for index, value := range nums {
		if value == target {
			if first == -1 {
				first = index
			}
			last = index
		}
	}
	return []int{first, last}
}
