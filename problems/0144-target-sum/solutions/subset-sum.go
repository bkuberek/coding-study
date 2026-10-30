package target_sum

func findTargetSumWays(nums []int, target int) int {
	total := 0
	for _, value := range nums {
		total += value
	}
	// With P the plus part: P - (total - P) = target, so P = (total + target) / 2.
	if target > total || target < -total || (total+target)%2 != 0 {
		return 0
	}
	plus := (total + target) / 2
	// ways[p] counts the subsets of the values seen so far that add up to p.
	ways := make([]int, plus+1)
	ways[0] = 1
	for _, value := range nums {
		// Decreasing p: ways[p-value] still excludes this value, so it is used at most once.
		for p := plus; p >= value; p-- {
			ways[p] += ways[p-value]
		}
	}
	return ways[plus]
}
