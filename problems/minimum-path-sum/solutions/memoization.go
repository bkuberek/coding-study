package minimum_path_sum

const unknown = -1

func minPathSum(grid [][]int) int {
	rows, columns := len(grid), len(grid[0])
	cheapest := make([][]int, rows)
	for row := range cheapest {
		cheapest[row] = make([]int, columns)
		for column := range cheapest[row] {
			cheapest[row][column] = unknown
		}
	}
	return cheapestTo(grid, cheapest, rows-1, columns-1)
}

func cheapestTo(grid, cheapest [][]int, row, column int) int {
	if cheapest[row][column] != unknown {
		return cheapest[row][column]
	}
	var arrival int
	switch {
	case row == 0 && column == 0:
		arrival = 0
	case row == 0:
		arrival = cheapestTo(grid, cheapest, row, column-1)
	case column == 0:
		arrival = cheapestTo(grid, cheapest, row-1, column)
	default:
		arrival = min(cheapestTo(grid, cheapest, row-1, column), cheapestTo(grid, cheapest, row, column-1))
	}
	cheapest[row][column] = arrival + grid[row][column]
	return cheapest[row][column]
}
