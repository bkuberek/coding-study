package longest_increasing_subsequence

func lengthOfLIS(nums []int) int {
	// ending[i] is the length of the longest increasing subsequence that ends at index i.
	ending := make([]int, len(nums))
	longest := 0
	for i := range nums {
		ending[i] = 1
		for j := 0; j < i; j++ {
			if nums[j] < nums[i] && ending[j]+1 > ending[i] {
				ending[i] = ending[j] + 1
			}
		}
		longest = max(longest, ending[i])
	}
	return longest
}
