package flood_fill

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func floodFill(grid [][]int, row int, col int, newColor int) [][]int {
	oldColor := grid[row][col]
	if oldColor == newColor {
		return grid
	}
	rows, cols := len(grid), len(grid[0])
	grid[row][col] = newColor
	queue := [][2]int{{row, col}}
	for len(queue) > 0 {
		cell := queue[0]
		queue = queue[1:]
		for _, step := range steps {
			nr, nc := cell[0]+step[0], cell[1]+step[1]
			if nr >= 0 && nr < rows && nc >= 0 && nc < cols && grid[nr][nc] == oldColor {
				grid[nr][nc] = newColor
				queue = append(queue, [2]int{nr, nc})
			}
		}
	}
	return grid
}
