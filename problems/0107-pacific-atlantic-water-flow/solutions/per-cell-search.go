package pacific_atlantic_water_flow

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func pacificAtlantic(heights [][]int) [][]int {
	rows, cols := len(heights), len(heights[0])
	// lastSeen holds, for each cell, the id of the last search that visited it, so no array is
	// reallocated or cleared per search. Ids start at 1.
	lastSeen := make([]int, rows*cols)

	drainsToBoth := func(id, startRow, startCol int) bool {
		pacific, atlantic := false, false
		lastSeen[startRow*cols+startCol] = id
		stack := [][2]int{{startRow, startCol}}
		for len(stack) > 0 {
			cell := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			r, c := cell[0], cell[1]
			pacific = pacific || r == 0 || c == 0
			atlantic = atlantic || r == rows-1 || c == cols-1
			if pacific && atlantic {
				return true
			}
			// Water runs to a neighbor that is not higher than the current cell.
			for _, step := range steps {
				nr, nc := r+step[0], c+step[1]
				if nr >= 0 && nr < rows && nc >= 0 && nc < cols &&
					lastSeen[nr*cols+nc] != id && heights[nr][nc] <= heights[r][c] {
					lastSeen[nr*cols+nc] = id
					stack = append(stack, [2]int{nr, nc})
				}
			}
		}
		return false
	}

	var result [][]int
	for r := 0; r < rows; r++ {
		for c := 0; c < cols; c++ {
			if drainsToBoth(r*cols+c+1, r, c) {
				result = append(result, []int{r, c})
			}
		}
	}
	return result
}
