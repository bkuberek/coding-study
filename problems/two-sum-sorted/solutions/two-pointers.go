package two_sum_sorted

func twoSumSorted(numbers []int, target int) []int {
	left, right := 0, len(numbers)-1
	for left < right {
		total := numbers[left] + numbers[right]
		switch {
		case total == target:
			return []int{left, right}
		case total < target:
			left++
		default:
			right--
		}
	}
	return nil
}
