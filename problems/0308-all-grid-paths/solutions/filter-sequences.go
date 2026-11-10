package all_grid_paths

func allGridPaths(n int) []string {
	steps := 2 * (n - 1)
	var paths []string
	moves := make([]byte, steps)
	// Counting up from 0 reads the bits from the most significant one as the first move, with
	// 0 for D and 1 for R, so the sequences come out in lexicographic order.
	for pattern := 0; pattern < 1<<steps; pattern++ {
		rights := 0
		for step := range moves {
			moves[step] = 'D'
			if (pattern>>(steps-1-step))&1 == 1 {
				moves[step] = 'R'
				rights++
			}
		}
		if rights == n-1 {
			paths = append(paths, string(moves))
		}
	}
	return paths
}
