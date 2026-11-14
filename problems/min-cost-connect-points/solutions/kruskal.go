package min_cost_connect_points

import "slices"

// Each pair is packed into one int as cost<<20 | i<<10 | j, so sorting the ints sorts the
// pairs by cost without allocating a struct per pair. Costs stay below 2^22 and indexes
// below 2^10.
const indexBits = 10

func minCostConnectPoints(points [][]int) int {
	n := len(points)
	pairs := make([]int, 0, n*(n-1)/2)
	for i := 0; i < n; i++ {
		for j := i + 1; j < n; j++ {
			cost := abs(points[i][0]-points[j][0]) + abs(points[i][1]-points[j][1])
			pairs = append(pairs, cost<<(2*indexBits)|i<<indexBits|j)
		}
	}
	slices.Sort(pairs)
	parent := make([]int, n)
	for node := range parent {
		parent[node] = node
	}
	find := func(node int) int {
		root := node
		for parent[root] != root {
			root = parent[root]
		}
		for parent[node] != root {
			parent[node], node = root, parent[node]
		}
		return root
	}
	total, cables := 0, 0
	// Take pairs from cheapest to most expensive, keeping each one that joins two groups.
	for _, pair := range pairs {
		if cables == n-1 {
			break
		}
		cost := pair >> (2 * indexBits)
		i := pair >> indexBits & (1<<indexBits - 1)
		j := pair & (1<<indexBits - 1)
		rootI, rootJ := find(i), find(j)
		if rootI != rootJ {
			parent[rootI] = rootJ
			total += cost
			cables++
		}
	}
	return total
}

func abs(value int) int {
	if value < 0 {
		return -value
	}
	return value
}
