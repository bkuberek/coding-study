package largest_rectangle_histogram

func largestRectangleArea(heights []int) int {
	best := 0
	for left := range heights {
		// The tallest rectangle spanning bars left..right is as high as the lowest of them.
		lowest := heights[left]
		for right := left; right < len(heights); right++ {
			lowest = min(lowest, heights[right])
			best = max(best, lowest*(right-left+1))
		}
	}
	return best
}
