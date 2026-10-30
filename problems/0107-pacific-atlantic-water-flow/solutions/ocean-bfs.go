package pacific_atlantic_water_flow

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func pacificAtlantic(heights [][]int) [][]int {
	rows, cols := len(heights), len(heights[0])

	// climb returns the cells whose water can reach a coast: it searches uphill from all the
	// coast cells at once.
	climb := func(coast [][2]int) [][]bool {
		reached := make([][]bool, rows)
		for r := range reached {
			reached[r] = make([]bool, cols)
		}
		var queue [][2]int
		for _, cell := range coast {
			// The corner shared by two sides of the coast is listed twice; enqueue it once.
			if !reached[cell[0]][cell[1]] {
				reached[cell[0]][cell[1]] = true
				queue = append(queue, cell)
			}
		}
		for len(queue) > 0 {
			cell := queue[0]
			queue = queue[1:]
			r, c := cell[0], cell[1]
			for _, step := range steps {
				nr, nc := r+step[0], c+step[1]
				if nr >= 0 && nr < rows && nc >= 0 && nc < cols &&
					!reached[nr][nc] && heights[nr][nc] >= heights[r][c] {
					reached[nr][nc] = true
					queue = append(queue, [2]int{nr, nc})
				}
			}
		}
		return reached
	}

	var pacificCoast, atlanticCoast [][2]int
	for c := 0; c < cols; c++ {
		pacificCoast = append(pacificCoast, [2]int{0, c})
		atlanticCoast = append(atlanticCoast, [2]int{rows - 1, c})
	}
	for r := 0; r < rows; r++ {
		pacificCoast = append(pacificCoast, [2]int{r, 0})
		atlanticCoast = append(atlanticCoast, [2]int{r, cols - 1})
	}
	pacific, atlantic := climb(pacificCoast), climb(atlanticCoast)

	var result [][]int
	for r := 0; r < rows; r++ {
		for c := 0; c < cols; c++ {
			if pacific[r][c] && atlantic[r][c] {
				result = append(result, []int{r, c})
			}
		}
	}
	return result
}
