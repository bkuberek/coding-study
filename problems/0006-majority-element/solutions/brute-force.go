package majority_element

func majorityElement(nums []int) int {
	half := len(nums) / 2
	for _, candidate := range nums {
		count := 0
		for _, value := range nums {
			if value == candidate {
				count++
			}
		}
		if count > half {
			return candidate
		}
	}
	panic("no majority element")
}
