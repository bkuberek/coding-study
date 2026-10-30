package subsets

func subsets(nums []int) [][]int {
	all := make([][]int, 0, 1<<len(nums))
	// Bit i of mask says whether nums[i] belongs to the subset that mask encodes.
	for mask := 0; mask < 1<<len(nums); mask++ {
		var subset []int
		for i, value := range nums {
			if mask>>i&1 == 1 {
				subset = append(subset, value)
			}
		}
		all = append(all, subset)
	}
	return all
}
