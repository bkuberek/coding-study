package rotting_oranges

const (
	freshOrange  = 1
	rottenOrange = 2
)

func touchesRotten(grid [][]int, r, c int) bool {
	rows, cols := len(grid), len(grid[0])
	steps := [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}
	for _, step := range steps {
		nr, nc := r+step[0], c+step[1]
		if nr >= 0 && nr < rows && nc >= 0 && nc < cols && grid[nr][nc] == rottenOrange {
			return true
		}
	}
	return false
}

func orangesRotting(grid [][]int) int {
	minutes := 0
	for {
		// Decide every change of this minute first, then apply them all: an orange that
		// turns now must not spread rot until the next minute.
		var turning [][2]int
		for r := range grid {
			for c := range grid[r] {
				if grid[r][c] == freshOrange && touchesRotten(grid, r, c) {
					turning = append(turning, [2]int{r, c})
				}
			}
		}
		if len(turning) == 0 {
			break
		}
		for _, cell := range turning {
			grid[cell[0]][cell[1]] = rottenOrange
		}
		minutes++
	}
	for _, row := range grid {
		for _, cell := range row {
			if cell == freshOrange {
				return -1
			}
		}
	}
	return minutes
}
