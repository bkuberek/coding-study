package shortest_path_binary_matrix

import "slices"

var steps = [8][2]int{{-1, -1}, {-1, 0}, {-1, 1}, {0, -1}, {0, 1}, {1, -1}, {1, 0}, {1, 1}}

func shortestPathBinaryMatrix(grid [][]int) int {
	n := len(grid)
	if grid[0][0] == 1 || grid[n-1][n-1] == 1 {
		return -1
	}
	unreached := n*n + 1
	dist := make([][]int, n)
	order := make([][2]int, 0, n*n)
	for r := range dist {
		dist[r] = make([]int, n)
		for c := range dist[r] {
			dist[r][c] = unreached
			order = append(order, [2]int{r, c})
		}
	}
	dist[0][0] = 1
	for changed := true; changed; {
		changed = false
		// Each sweep lets every open cell take the best distance offered by a neighbor.
		for _, cell := range order {
			r, c := cell[0], cell[1]
			if grid[r][c] == 1 {
				continue
			}
			for _, step := range steps {
				nr, nc := r+step[0], c+step[1]
				if nr >= 0 && nr < n && nc >= 0 && nc < n && dist[nr][nc]+1 < dist[r][c] {
					dist[r][c] = dist[nr][nc] + 1
					changed = true
				}
			}
		}
		// Alternating the scan direction lets improvements travel both ways quickly.
		slices.Reverse(order)
	}
	best := dist[n-1][n-1]
	if best < unreached {
		return best
	}
	return -1
}
