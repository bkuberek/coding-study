package majority_element

func majorityElement(nums []int) int {
	candidate, votes := nums[0], 0
	for _, value := range nums {
		if votes == 0 {
			candidate = value
		}
		if value == candidate {
			votes++
		} else {
			votes--
		}
	}
	return candidate
}
