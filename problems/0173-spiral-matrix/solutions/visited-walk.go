package spiral_matrix

// directions are right, down, left, up: clockwise.
var directions = [4][2]int{{0, 1}, {1, 0}, {0, -1}, {-1, 0}}

func spiralOrder(matrix [][]int) []int {
	rows, cols := len(matrix), len(matrix[0])
	visited := make([][]bool, rows)
	for r := range visited {
		visited[r] = make([]bool, cols)
	}
	order := make([]int, 0, rows*cols)
	r, c, heading := 0, 0, 0
	for range rows * cols {
		order = append(order, matrix[r][c])
		visited[r][c] = true
		nr, nc := r+directions[heading][0], c+directions[heading][1]
		if nr < 0 || nr >= rows || nc < 0 || nc >= cols || visited[nr][nc] {
			heading = (heading + 1) % 4
			nr, nc = r+directions[heading][0], c+directions[heading][1]
		}
		r, c = nr, nc
	}
	return order
}
