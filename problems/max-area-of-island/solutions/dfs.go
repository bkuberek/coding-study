package max_area_of_island

func maxAreaOfIsland(grid [][]int) int {
	rows, cols := len(grid), len(grid[0])
	seen := make([][]bool, rows)
	for row := range seen {
		seen[row] = make([]bool, cols)
	}
	steps := [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}
	best := 0
	for row := range grid {
		for col := range grid[row] {
			if grid[row][col] != 1 || seen[row][col] {
				continue
			}
			seen[row][col] = true
			stack := [][2]int{{row, col}}
			area := 0
			for len(stack) > 0 {
				cell := stack[len(stack)-1]
				stack = stack[:len(stack)-1]
				area++
				for _, step := range steps {
					nextRow, nextCol := cell[0]+step[0], cell[1]+step[1]
					if nextRow >= 0 && nextRow < rows && nextCol >= 0 && nextCol < cols &&
						grid[nextRow][nextCol] == 1 && !seen[nextRow][nextCol] {
						seen[nextRow][nextCol] = true
						stack = append(stack, [2]int{nextRow, nextCol})
					}
				}
			}
			best = max(best, area)
		}
	}
	return best
}
