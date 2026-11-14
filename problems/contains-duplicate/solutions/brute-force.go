package contains_duplicate

func containsDuplicate(nums []int) bool {
	for i, value := range nums {
		for _, later := range nums[i+1:] {
			if later == value {
				return true
			}
		}
	}
	return false
}
