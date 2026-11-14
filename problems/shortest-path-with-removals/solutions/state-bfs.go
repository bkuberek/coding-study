package shortest_path_with_removals

type state struct {
	row, col, used int
}

func shortestPath(grid [][]int, k int) int {
	rows, cols := len(grid), len(grid[0])
	// A Manhattan route enters at most rows + cols - 3 cells besides the corners, so more
	// removals than that never help.
	budget := min(k, max(0, rows+cols-3))
	seen := make([][][]bool, rows)
	for r := range seen {
		seen[r] = make([][]bool, cols)
		for c := range seen[r] {
			seen[r][c] = make([]bool, budget+1)
		}
	}
	seen[0][0][0] = true
	steps := [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}
	queue := []state{{0, 0, 0}}
	for moves := 0; len(queue) > 0; moves++ {
		for level := len(queue); level > 0; level-- {
			current := queue[0]
			queue = queue[1:]
			if current.row == rows-1 && current.col == cols-1 {
				return moves
			}
			for _, step := range steps {
				nr, nc := current.row+step[0], current.col+step[1]
				if nr < 0 || nr >= rows || nc < 0 || nc >= cols {
					continue
				}
				after := current.used + grid[nr][nc]
				if after <= budget && !seen[nr][nc][after] {
					seen[nr][nc][after] = true
					queue = append(queue, state{nr, nc, after})
				}
			}
		}
	}
	return -1
}
