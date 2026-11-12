package path_exists_in_graph

func hasPath(n int, edges [][]int, source int, target int) bool {
	// neighbors[node] lists every node joined to `node`; each connection works both ways.
	neighbors := make([][]int, n)
	for _, edge := range edges {
		a, b := edge[0], edge[1]
		neighbors[a] = append(neighbors[a], b)
		neighbors[b] = append(neighbors[b], a)
	}
	seen := make([]bool, n)
	seen[source] = true
	queue := []int{source}
	for len(queue) > 0 {
		node := queue[0]
		queue = queue[1:]
		if node == target {
			return true
		}
		for _, neighbor := range neighbors[node] {
			if !seen[neighbor] {
				seen[neighbor] = true
				queue = append(queue, neighbor)
			}
		}
	}
	return false
}
