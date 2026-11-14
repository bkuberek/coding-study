package cheapest_flights_k_stops

import "container/heap"

type state struct {
	price, city, used int
}

// stateHeap is a min-heap of states ordered by price; container/heap supplies the sifting.
type stateHeap []state

func (h stateHeap) Len() int           { return len(h) }
func (h stateHeap) Less(i, j int) bool { return h[i].price < h[j].price }
func (h stateHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *stateHeap) Push(x any)        { *h = append(*h, x.(state)) }
func (h *stateHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

type edge struct {
	to, cost int
}

func findCheapestPrice(n int, flights [][]int, src int, dst int, k int) int {
	graph := make([][]edge, n)
	for _, flight := range flights {
		graph[flight[0]] = append(graph[flight[0]], edge{flight[1], flight[2]})
	}
	// fewest[c] is the fewest flights with which c was settled so far. States are popped in
	// order of price, so a later state for c is useful only if it used fewer flights.
	fewest := make([]int, n)
	for city := range fewest {
		fewest[city] = k + 2
	}
	pending := &stateHeap{{0, src, 0}}
	for pending.Len() > 0 {
		current := heap.Pop(pending).(state)
		if current.city == dst {
			return current.price
		}
		if current.used >= fewest[current.city] {
			continue
		}
		fewest[current.city] = current.used
		if current.used == k+1 {
			continue // no flights left
		}
		for _, next := range graph[current.city] {
			heap.Push(pending, state{current.price + next.cost, next.to, current.used + 1})
		}
	}
	return -1
}
