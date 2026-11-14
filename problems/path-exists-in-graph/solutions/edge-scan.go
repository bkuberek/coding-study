package path_exists_in_graph

func hasPath(n int, edges [][]int, source int, target int) bool {
	reached := make([]bool, n)
	reached[source] = true
	for changed := true; changed && !reached[target]; {
		changed = false
		for _, edge := range edges {
			a, b := edge[0], edge[1]
			// A connection with exactly one reached end brings the other end in.
			if reached[a] != reached[b] {
				reached[a], reached[b] = true, true
				changed = true
			}
		}
	}
	return reached[target]
}
