package unique_paths

const mod = 1_000_000_007

func uniquePaths(m int, n int) int {
	// routes[row][column] is the number of routes from the start to that cell. The first row
	// and the first column can only be reached in a straight line.
	routes := make([][]int, m)
	for row := range routes {
		routes[row] = make([]int, n)
		for column := range routes[row] {
			routes[row][column] = 1
		}
	}
	for row := 1; row < m; row++ {
		for column := 1; column < n; column++ {
			routes[row][column] = (routes[row-1][column] + routes[row][column-1]) % mod
		}
	}
	return routes[m-1][n-1]
}
