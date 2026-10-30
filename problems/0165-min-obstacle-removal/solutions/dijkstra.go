package min_obstacle_removal

import "container/heap"

var directions = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

// entry is a cell with the removals needed to reach it.
type entry struct {
	cost, r, c int
}

// entryHeap is a min-heap of entries ordered by cost; container/heap supplies the sifting.
type entryHeap []entry

func (h entryHeap) Len() int           { return len(h) }
func (h entryHeap) Less(i, j int) bool { return h[i].cost < h[j].cost }
func (h entryHeap) Swap(i, j int)      { h[i], h[j] = h[j], h[i] }
func (h *entryHeap) Push(x any)        { *h = append(*h, x.(entry)) }
func (h *entryHeap) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func minimumObstacles(grid [][]int) int {
	rows, cols := len(grid), len(grid[0])
	removals := make([][]int, rows)
	for r := range removals {
		removals[r] = make([]int, cols)
		for c := range removals[r] {
			removals[r][c] = -1 // not settled yet
		}
	}
	// Entering a cell costs its own value.
	pending := &entryHeap{{0, 0, 0}}
	for pending.Len() > 0 {
		current := heap.Pop(pending).(entry)
		r, c := current.r, current.c
		if removals[r][c] != -1 {
			continue // an outdated entry: the cell was settled earlier at a lower cost
		}
		removals[r][c] = current.cost
		if r == rows-1 && c == cols-1 {
			return current.cost
		}
		for _, d := range directions {
			nr, nc := r+d[0], c+d[1]
			if nr >= 0 && nr < rows && nc >= 0 && nc < cols && removals[nr][nc] == -1 {
				heap.Push(pending, entry{current.cost + grid[nr][nc], nr, nc})
			}
		}
	}
	panic("the goal is always reachable when every obstacle may be removed")
}
