package city_fewest_neighbors

import "math"

// inf marks a missing road; half of the largest int keeps the sum of two of them from overflowing.
const inf = math.MaxInt / 2

func findTheCity(n int, edges [][]int, distanceThreshold int) int {
	dist := make([][]int, n)
	for city := range dist {
		dist[city] = make([]int, n)
		for other := range dist[city] {
			dist[city][other] = inf
		}
		dist[city][city] = 0
	}
	for _, road := range edges {
		a, b, w := road[0], road[1], road[2]
		dist[a][b], dist[b][a] = w, w
	}
	// After step middle, dist[i][j] is the shortest route that only passes through cities 0..middle.
	for middle := 0; middle < n; middle++ {
		through := dist[middle]
		for i := 0; i < n; i++ {
			toMiddle := dist[i][middle]
			if toMiddle == inf {
				continue
			}
			row := dist[i]
			for j := 0; j < n; j++ {
				if toMiddle+through[j] < row[j] {
					row[j] = toMiddle + through[j]
				}
			}
		}
	}
	bestCity, bestCount := -1, n+1
	for city := 0; city < n; city++ {
		count := 0
		for other := 0; other < n; other++ {
			if other != city && dist[city][other] <= distanceThreshold {
				count++
			}
		}
		// `<=` lets a later city win a tie.
		if count <= bestCount {
			bestCity, bestCount = city, count
		}
	}
	return bestCity
}
