package redundant_connection

func findRedundantConnection(edges [][]int) []int {
	neighbors := make([][]int, len(edges)+1)

	connected := func(start, goal int) bool {
		seen := map[int]bool{start: true}
		stack := []int{start}
		for len(stack) > 0 {
			node := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			if node == goal {
				return true
			}
			for _, neighbor := range neighbors[node] {
				if !seen[neighbor] {
					seen[neighbor] = true
					stack = append(stack, neighbor)
				}
			}
		}
		return false
	}

	for _, edge := range edges {
		a, b := edge[0], edge[1]
		// The first edge whose ends are already connected closes the only cycle.
		if connected(a, b) {
			return []int{a, b}
		}
		neighbors[a] = append(neighbors[a], b)
		neighbors[b] = append(neighbors[b], a)
	}
	return nil
}
