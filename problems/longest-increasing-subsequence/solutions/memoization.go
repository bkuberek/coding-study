package longest_increasing_subsequence

func lengthOfLIS(nums []int) int {
	memo := make([]int, len(nums)) // 0 means "not computed yet": every start has length at least 1

	// longestFrom returns the length of the longest increasing subsequence whose first
	// element is nums[start].
	var longestFrom func(start int) int
	longestFrom = func(start int) int {
		if memo[start] == 0 {
			best := 1
			for following := start + 1; following < len(nums); following++ {
				if nums[following] > nums[start] {
					best = max(best, 1+longestFrom(following))
				}
			}
			memo[start] = best
		}
		return memo[start]
	}

	longest := 0
	for start := range nums {
		longest = max(longest, longestFrom(start))
	}
	return longest
}
