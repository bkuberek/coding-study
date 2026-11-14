package unique_paths

const mod = 1_000_000_007

func uniquePaths(m int, n int) int {
	// Transposing the grid does not change the count, so keep the row along the shorter side.
	width, height := min(m, n), max(m, n)
	// Before the update, routes[column] belongs to the row above; after it, to the current row.
	routes := make([]int, width)
	for column := range routes {
		routes[column] = 1
	}
	for row := 1; row < height; row++ {
		for column := 1; column < width; column++ {
			routes[column] = (routes[column] + routes[column-1]) % mod
		}
	}
	return routes[width-1]
}
