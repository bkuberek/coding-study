package all_grid_paths

func allGridPaths(n int) []string {
	last := n - 1
	var paths []string
	moves := make([]byte, 0, 2*last)

	var extend func(downs, rights int)
	extend = func(downs, rights int) {
		if downs == last && rights == last {
			paths = append(paths, string(moves))
			return
		}
		// D is tried before R, so the paths come out in lexicographic order.
		if downs < last {
			moves = append(moves, 'D')
			extend(downs+1, rights)
			moves = moves[:len(moves)-1]
		}
		if rights < last {
			moves = append(moves, 'R')
			extend(downs, rights+1)
			moves = moves[:len(moves)-1]
		}
	}

	extend(0, 0)
	return paths
}
