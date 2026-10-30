package number_of_islands

const (
	land  = '1'
	water = '0'
)

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func numIslands(grid [][]rune) int {
	rows, cols := len(grid), len(grid[0])
	islands := 0
	for row := 0; row < rows; row++ {
		for col := 0; col < cols; col++ {
			if grid[row][col] != land {
				continue
			}
			islands++
			// Sink the island: every land square becomes water as soon as it is discovered,
			// so it is pushed at most once and never counted again.
			grid[row][col] = water
			stack := [][2]int{{row, col}}
			for len(stack) > 0 {
				cell := stack[len(stack)-1]
				stack = stack[:len(stack)-1]
				for _, step := range steps {
					nr, nc := cell[0]+step[0], cell[1]+step[1]
					if nr >= 0 && nr < rows && nc >= 0 && nc < cols && grid[nr][nc] == land {
						grid[nr][nc] = water
						stack = append(stack, [2]int{nr, nc})
					}
				}
			}
		}
	}
	return islands
}
