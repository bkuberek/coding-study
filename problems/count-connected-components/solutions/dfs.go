package count_connected_components

func countComponents(n int, edges [][]int) int {
	neighbors := make([][]int, n)
	for _, edge := range edges {
		a, b := edge[0], edge[1]
		neighbors[a] = append(neighbors[a], b)
		neighbors[b] = append(neighbors[b], a)
	}
	seen := make([]bool, n)
	components := 0
	for start := range seen {
		if seen[start] {
			continue
		}
		components++
		seen[start] = true
		stack := []int{start} // an explicit stack avoids deep recursion on long paths
		for len(stack) > 0 {
			node := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			for _, neighbor := range neighbors[node] {
				if !seen[neighbor] {
					seen[neighbor] = true
					stack = append(stack, neighbor)
				}
			}
		}
	}
	return components
}
