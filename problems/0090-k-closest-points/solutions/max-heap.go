package k_closest_points

import "container/heap"

// entry is a kept point: its squared distance and its position in the input.
type entry struct {
	distance, index int
}

// farthestFirst implements heap.Interface with the farthest kept point at index 0.
type farthestFirst []entry

func (h farthestFirst) Len() int           { return len(h) }
func (h farthestFirst) Less(i, j int) bool { return h[i].distance > h[j].distance }
func (h farthestFirst) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }

func (h *farthestFirst) Push(kept any) {
	*h = append(*h, kept.(entry))
}

func (h *farthestFirst) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func kClosest(points [][]int, k int) [][]int {
	kept := make(farthestFirst, 0, k)
	for index, point := range points {
		distance := point[0]*point[0] + point[1]*point[1]
		if len(kept) < k {
			heap.Push(&kept, entry{distance, index})
		} else if distance < kept[0].distance {
			kept[0] = entry{distance, index}
			heap.Fix(&kept, 0)
		}
	}
	closest := make([][]int, 0, k)
	for _, e := range kept {
		closest = append(closest, points[e.index])
	}
	return closest
}
