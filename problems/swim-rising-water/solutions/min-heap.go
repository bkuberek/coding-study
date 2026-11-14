package swim_rising_water

import "container/heap"

var directions = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

// entry is a cell with the highest floor on the route that reached it.
type entry struct {
	level, r, c int
}

// entryHeap is a min-heap of entries ordered by level; container/heap supplies the sifting.
type entryHeap []entry

func (h entryHeap) Len() int           { return len(h) }
func (h entryHeap) Less(i, j int) bool { return h[i].level < h[j].level }
func (h entryHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *entryHeap) Push(x any)        { *h = append(*h, x.(entry)) }
func (h *entryHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func swimInWater(grid [][]int) int {
	n := len(grid)
	seen := make([][]bool, n)
	for r := range seen {
		seen[r] = make([]bool, n)
	}
	seen[0][0] = true
	pending := &entryHeap{{grid[0][0], 0, 0}}
	for pending.Len() > 0 {
		current := heap.Pop(pending).(entry)
		if current.r == n-1 && current.c == n-1 {
			return current.level
		}
		for _, d := range directions {
			nr, nc := current.r+d[0], current.c+d[1]
			if nr >= 0 && nr < n && nc >= 0 && nc < n && !seen[nr][nc] {
				seen[nr][nc] = true
				heap.Push(pending, entry{max(current.level, grid[nr][nc]), nr, nc})
			}
		}
	}
	panic("the goal is always reachable once the water covers every floor")
}
