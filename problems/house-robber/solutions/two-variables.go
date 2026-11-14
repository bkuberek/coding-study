package house_robber

func rob(nums []int) int {
	// Before each house: withoutLast and withLast are the best totals for the prefixes
	// that end two houses back and one house back.
	withoutLast, withLast := 0, 0
	for _, cash := range nums {
		withoutLast, withLast = withLast, max(withLast, withoutLast+cash)
	}
	return withLast
}
