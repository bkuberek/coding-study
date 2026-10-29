package largest_rectangle_histogram

func largestRectangleArea(heights []int) int {
	best := 0
	// Indexes of bars whose heights strictly increase from bottom to top.
	var rising []int
	// One extra bar of height 0 at the end pops every bar still waiting.
	for index := 0; index <= len(heights); index++ {
		height := 0
		if index < len(heights) {
			height = heights[index]
		}
		for len(rising) > 0 && heights[rising[len(rising)-1]] >= height {
			top := rising[len(rising)-1]
			rising = rising[:len(rising)-1]
			// The bar below top on the stack is lower, and so is index (or it is equal and a
			// later pop covers the full width): the rectangle spans the bars between them.
			left := -1
			if len(rising) > 0 {
				left = rising[len(rising)-1]
			}
			best = max(best, heights[top]*(index-left-1))
		}
		rising = append(rising, index)
	}
	return best
}
