package min_cost_connect_points

import "math"

func minCostConnectPoints(points [][]int) int {
	n := len(points)
	// cheapest[i] is the cheapest cable from point i to the tree built so far.
	cheapest := make([]int, n)
	for i := range cheapest {
		cheapest[i] = math.MaxInt
	}
	inTree := make([]bool, n)
	cheapest[0] = 0
	total := 0
	for round := 0; round < n; round++ {
		point := -1
		for i := 0; i < n; i++ {
			if !inTree[i] && (point < 0 || cheapest[i] < cheapest[point]) {
				point = i
			}
		}
		inTree[point] = true
		total += cheapest[point]
		x, y := points[point][0], points[point][1]
		for other := 0; other < n; other++ {
			if !inTree[other] {
				cost := abs(x-points[other][0]) + abs(y-points[other][1])
				cheapest[other] = min(cheapest[other], cost)
			}
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
