package number_of_islands

const land = '1'

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func numIslands(grid [][]rune) int {
	rows, cols := len(grid), len(grid[0])
	visited := make([][]bool, rows)
	for row := range visited {
		visited[row] = make([]bool, cols)
	}
	islands := 0
	for row := 0; row < rows; row++ {
		for col := 0; col < cols; col++ {
			if grid[row][col] != land || visited[row][col] {
				continue
			}
			islands++
			visited[row][col] = true
			queue := [][2]int{{row, col}}
			for len(queue) > 0 {
				cell := queue[0]
				queue = queue[1:]
				for _, step := range steps {
					nr, nc := cell[0]+step[0], cell[1]+step[1]
					if nr >= 0 && nr < rows && nc >= 0 && nc < cols && grid[nr][nc] == land && !visited[nr][nc] {
						visited[nr][nc] = true
						queue = append(queue, [2]int{nr, nc})
					}
				}
			}
		}
	}
	return islands
}
