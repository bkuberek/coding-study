package city_fewest_neighbors

import "container/heap"

type road struct {
	to, weight int
}

type visit struct {
	distance, city int
}

// visitHeap is a min-heap of visits ordered by distance; container/heap supplies the sifting.
type visitHeap []visit

func (h visitHeap) Len() int           { return len(h) }
func (h visitHeap) Less(i, j int) bool { return h[i].distance < h[j].distance }
func (h visitHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *visitHeap) Push(x any)        { *h = append(*h, x.(visit)) }
func (h *visitHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func findTheCity(n int, edges [][]int, distanceThreshold int) int {
	graph := make([][]road, n)
	for _, edge := range edges {
		a, b, w := edge[0], edge[1], edge[2]
		graph[a] = append(graph[a], road{b, w})
		graph[b] = append(graph[b], road{a, w})
	}

	// reachable counts the other cities within the threshold, stopping once distances exceed it.
	reachable := func(source int) int {
		settled := make([]bool, n)
		count := -1 // the source settles first and is not its own neighbor
		pending := &visitHeap{{0, source}}
		for pending.Len() > 0 {
			current := heap.Pop(pending).(visit)
			if current.distance > distanceThreshold {
				break
			}
			if settled[current.city] {
				continue
			}
			settled[current.city] = true
			count++
			for _, next := range graph[current.city] {
				if !settled[next.to] && current.distance+next.weight <= distanceThreshold {
					heap.Push(pending, visit{current.distance + next.weight, next.to})
				}
			}
		}
		return count
	}

	bestCity, bestCount := -1, n+1
	for city := 0; city < n; city++ {
		count := reachable(city)
		// `<=` lets a later city win a tie.
		if count <= bestCount {
			bestCity, bestCount = city, count
		}
	}
	return bestCity
}
