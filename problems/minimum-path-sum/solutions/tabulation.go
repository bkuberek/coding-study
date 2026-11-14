package minimum_path_sum

func minPathSum(grid [][]int) int {
	rows, columns := len(grid), len(grid[0])
	// cheapest[r][c]: the smallest total toll of any route from the top-left block to block (r, c).
	cheapest := make([][]int, rows)
	for row := range cheapest {
		cheapest[row] = make([]int, columns)
	}
	for row := 0; row < rows; row++ {
		for column := 0; column < columns; column++ {
			var arrival int
			switch {
			case row == 0 && column == 0:
				arrival = 0
			case row == 0:
				arrival = cheapest[row][column-1]
			case column == 0:
				arrival = cheapest[row-1][column]
			default:
				arrival = min(cheapest[row-1][column], cheapest[row][column-1])
			}
			cheapest[row][column] = arrival + grid[row][column]
		}
	}
	return cheapest[rows-1][columns-1]
}
