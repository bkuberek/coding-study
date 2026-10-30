package critical_connections

func criticalConnections(n int, connections [][]int) [][]int {
	adjacency := make([][]int, n)
	for _, cable := range connections {
		a, b := cable[0], cable[1]
		adjacency[a] = append(adjacency[a], b)
		adjacency[b] = append(adjacency[b], a)
	}
	// discovered[v] is the order in which v was first reached (-1: not yet).
	// low[v] is the earliest discovery time reachable from v's subtree using at most one
	// cable that is not a tree edge.
	discovered := make([]int, n)
	for server := range discovered {
		discovered[server] = -1
	}
	low := make([]int, n)
	bridges := [][]int{}
	clock := 0

	var visit func(server, parent int)
	visit = func(server, parent int) {
		discovered[server], low[server] = clock, clock
		clock++
		for _, neighbor := range adjacency[server] {
			if neighbor == parent {
				continue // the tree edge we arrived by is not a way back
			}
			if discovered[neighbor] == -1 {
				visit(neighbor, server)
				low[server] = min(low[server], low[neighbor])
				if low[neighbor] > discovered[server] {
					bridges = append(bridges, []int{server, neighbor})
				}
			} else {
				low[server] = min(low[server], discovered[neighbor])
			}
		}
	}

	visit(0, -1)
	return bridges
}
