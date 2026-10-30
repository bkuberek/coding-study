package house_robber

func rob(nums []int) int {
	// best[i] is the most cash obtainable from the first i houses.
	best := make([]int, len(nums)+1)
	best[1] = nums[0]
	for i := 2; i <= len(nums); i++ {
		best[i] = max(best[i-1], best[i-2]+nums[i-1])
	}
	return best[len(nums)]
}
