package min_obstacle_removal

import "container/list"

var directions = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func minimumObstacles(grid [][]int) int {
	rows, cols := len(grid), len(grid[0])
	unreached := rows * cols
	removals := make([][]int, rows)
	for r := range removals {
		removals[r] = make([]int, cols)
		for c := range removals[r] {
			removals[r][c] = unreached
		}
	}
	removals[0][0] = 0
	// The deque stays sorted by removals: zero-cost steps go to the front, one-cost steps
	// to the back, so its two ends never differ by more than one.
	queue := list.New()
	queue.PushBack([2]int{0, 0})
	for queue.Len() > 0 {
		cell := queue.Remove(queue.Front()).([2]int)
		r, c := cell[0], cell[1]
		cost := removals[r][c]
		if r == rows-1 && c == cols-1 {
			return cost
		}
		for _, d := range directions {
			nr, nc := r+d[0], c+d[1]
			if nr >= 0 && nr < rows && nc >= 0 && nc < cols && cost+grid[nr][nc] < removals[nr][nc] {
				removals[nr][nc] = cost + grid[nr][nc]
				if grid[nr][nc] == 0 {
					queue.PushFront([2]int{nr, nc})
				} else {
					queue.PushBack([2]int{nr, nc})
				}
			}
		}
	}
	return removals[rows-1][cols-1]
}
