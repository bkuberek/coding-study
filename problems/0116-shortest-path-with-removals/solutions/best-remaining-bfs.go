package shortest_path_with_removals

type visit struct {
	row, col, left int
}

func shortestPath(grid [][]int, k int) int {
	rows, cols := len(grid), len(grid[0])
	shortest := rows + cols - 2
	// Enough removals for the straight Manhattan route: nothing can beat it.
	if k >= rows+cols-3 {
		return shortest
	}
	// best[r][c] is the most removals left with which (r, c) was reached so far.
	best := make([][]int, rows)
	for r := range best {
		best[r] = make([]int, cols)
		for c := range best[r] {
			best[r][c] = -1
		}
	}
	best[0][0] = k
	steps := [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}
	queue := []visit{{0, 0, k}}
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
				remaining := current.left - grid[nr][nc]
				// A visit that arrives later with no more removals left can never do better.
				if remaining > best[nr][nc] {
					best[nr][nc] = remaining
					queue = append(queue, visit{nr, nc, remaining})
				}
			}
		}
	}
	return -1
}
