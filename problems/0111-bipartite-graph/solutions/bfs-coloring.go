package bipartite_graph

const uncolored = -1

func isBipartite(graph [][]int) bool {
	color := make([]int, len(graph))
	for node := range color {
		color[node] = uncolored
	}
	// Every piece of the graph needs its own start node.
	for start := range graph {
		if color[start] != uncolored {
			continue
		}
		color[start] = 0
		queue := []int{start}
		for len(queue) > 0 {
			node := queue[0]
			queue = queue[1:]
			for _, neighbor := range graph[node] {
				if color[neighbor] == uncolored {
					color[neighbor] = 1 - color[node]
					queue = append(queue, neighbor)
				} else if color[neighbor] == color[node] {
					return false
				}
			}
		}
	}
	return true
}
