package flood_fill

func floodFill(grid [][]int, row int, col int, newColor int) [][]int {
	oldColor := grid[row][col]
	if oldColor == newColor {
		return grid
	}
	var paint func(r, c int)
	paint = func(r, c int) {
		if r < 0 || r >= len(grid) || c < 0 || c >= len(grid[0]) || grid[r][c] != oldColor {
			return
		}
		grid[r][c] = newColor
		paint(r+1, c)
		paint(r-1, c)
		paint(r, c+1)
		paint(r, c-1)
	}
	paint(row, col)
	return grid
}
