package top_k_frequent_elements

func topKFrequent(nums []int, k int) []int {
	counts := make(map[int]int)
	for _, value := range nums {
		counts[value]++
	}
	// buckets[c] holds the values that occur exactly c times; no count exceeds len(nums).
	buckets := make([][]int, len(nums)+1)
	for value, count := range counts {
		buckets[count] = append(buckets[count], value)
	}
	answer := make([]int, 0, k)
	for count := len(nums); count > 0; count-- {
		for _, value := range buckets[count] {
			answer = append(answer, value)
			if len(answer) == k {
				return answer
			}
		}
	}
	return answer
}
