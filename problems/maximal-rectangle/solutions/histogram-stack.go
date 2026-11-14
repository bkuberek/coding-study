package maximal_rectangle

func maximalRectangle(matrix [][]rune) int {
	// heights[c] counts the consecutive ones in column c ending at the current row.
	heights := make([]int, len(matrix[0]))
	best := 0
	for _, row := range matrix {
		for c, cell := range row {
			if cell == '1' {
				heights[c]++
			} else {
				heights[c] = 0
			}
		}
		best = max(best, largestInHistogram(heights))
	}
	return best
}

func largestInHistogram(heights []int) int {
	best := 0
	// Indexes of bars whose heights strictly increase from bottom to top.
	rising := make([]int, 0, len(heights)+1)
	// One extra bar of height 0 at the end pops every bar still waiting.
	for index := 0; index <= len(heights); index++ {
		height := 0
		if index < len(heights) {
			height = heights[index]
		}
		for len(rising) > 0 && heights[rising[len(rising)-1]] >= height {
			top := rising[len(rising)-1]
			rising = rising[:len(rising)-1]
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
