package two_sum

func twoSum(nums []int, target int) []int {
	indexByValue := make(map[int]int, len(nums))
	for i, value := range nums {
		if partner, ok := indexByValue[target-value]; ok {
			return []int{partner, i}
		}
		indexByValue[value] = i
	}
	return nil
}
