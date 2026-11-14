package majority_element

func majorityElement(nums []int) int {
	half := len(nums) / 2
	counts := make(map[int]int, len(nums))
	for _, value := range nums {
		counts[value]++
		if counts[value] > half {
			return value
		}
	}
	panic("no majority element")
}
