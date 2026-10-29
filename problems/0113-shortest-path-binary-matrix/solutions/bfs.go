package shortest_path_binary_matrix

var steps = [8][2]int{{-1, -1}, {-1, 0}, {-1, 1}, {0, -1}, {0, 1}, {1, -1}, {1, 0}, {1, 1}}

func shortestPathBinaryMatrix(grid [][]int) int {
	n := len(grid)
	if grid[0][0] == 1 || grid[n-1][n-1] == 1 {
		return -1
	}
	dist := make([][]int, n)
	for r := range dist {
		dist[r] = make([]int, n)
	}
	dist[0][0] = 1
	queue := [][2]int{{0, 0}}
	for len(queue) > 0 {
		cell := queue[0]
		queue = queue[1:]
		r, c := cell[0], cell[1]
		if r == n-1 && c == n-1 {
			return dist[r][c]
		}
		for _, step := range steps {
			nr, nc := r+step[0], c+step[1]
			// dist 0 means "not reached yet": every reached cell has length at least 1.
			if nr >= 0 && nr < n && nc >= 0 && nc < n && grid[nr][nc] == 0 && dist[nr][nc] == 0 {
				dist[nr][nc] = dist[r][c] + 1
				queue = append(queue, [2]int{nr, nc})
			}
		}
	}
	return -1
}
