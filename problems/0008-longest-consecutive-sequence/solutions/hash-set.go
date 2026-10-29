package longest_consecutive_sequence

func longestConsecutive(nums []int) int {
	present := make(map[int]bool, len(nums))
	for _, value := range nums {
		present[value] = true
	}
	longest := 0
	for value := range present {
		if present[value-1] {
			continue
		}
		end := value + 1
		for present[end] {
			end++
		}
		longest = max(longest, end-value)
	}
	return longest
}
