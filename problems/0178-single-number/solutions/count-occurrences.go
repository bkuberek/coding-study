package single_number

func singleNumber(nums []int) int {
	counts := make(map[int]int, len(nums))
	for _, value := range nums {
		counts[value]++
	}
	for value, count := range counts {
		if count == 1 {
			return value
		}
	}
	panic("exactly one value occurs once")
}
