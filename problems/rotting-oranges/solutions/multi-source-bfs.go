package rotting_oranges

const (
	freshOrange  = 1
	rottenOrange = 2
)

func orangesRotting(grid [][]int) int {
	rows, cols := len(grid), len(grid[0])
	var queue [][2]int
	fresh := 0
	for r := range grid {
		for c := range grid[r] {
			switch grid[r][c] {
			case rottenOrange:
				queue = append(queue, [2]int{r, c})
			case freshOrange:
				fresh++
			}
		}
	}
	steps := [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}
	minutes := 0
	// Each pass of the outer loop is one minute: it rots the whole current frontier.
	for len(queue) > 0 && fresh > 0 {
		minutes++
		for frontier := len(queue); frontier > 0; frontier-- {
			cell := queue[0]
			queue = queue[1:]
			for _, step := range steps {
				nr, nc := cell[0]+step[0], cell[1]+step[1]
				if nr >= 0 && nr < rows && nc >= 0 && nc < cols && grid[nr][nc] == freshOrange {
					grid[nr][nc] = rottenOrange
					fresh--
					queue = append(queue, [2]int{nr, nc})
				}
			}
		}
	}
	if fresh == 0 {
		return minutes
	}
	return -1
}
