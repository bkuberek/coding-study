package unique_paths

const mod = 1_000_000_007

func uniquePaths(m int, n int) int {
	// routes[row][column] caches the number of routes from that cell to the goal; -1 is unknown.
	routes := make([][]int, m)
	for row := range routes {
		routes[row] = make([]int, n)
		for column := range routes[row] {
			routes[row][column] = -1
		}
	}
	var count func(row, column int) int
	count = func(row, column int) int {
		if row == m-1 || column == n-1 {
			return 1
		}
		if routes[row][column] < 0 {
			routes[row][column] = (count(row+1, column) + count(row, column+1)) % mod
		}
		return routes[row][column]
	}
	return count(0, 0)
}
