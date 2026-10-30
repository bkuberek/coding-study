package swim_rising_water

var directions = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func swimInWater(grid [][]int) int {
	n := len(grid)

	// reachable reports whether the goal can be reached when the water stands at `time`.
	reachable := func(time int) bool {
		if grid[0][0] > time {
			return false
		}
		seen := make([][]bool, n)
		for r := range seen {
			seen[r] = make([]bool, n)
		}
		seen[0][0] = true
		queue := [][2]int{{0, 0}}
		for head := 0; head < len(queue); head++ {
			r, c := queue[head][0], queue[head][1]
			if r == n-1 && c == n-1 {
				return true
			}
			for _, d := range directions {
				nr, nc := r+d[0], c+d[1]
				if nr >= 0 && nr < n && nc >= 0 && nc < n && !seen[nr][nc] && grid[nr][nc] <= time {
					seen[nr][nc] = true
					queue = append(queue, [2]int{nr, nc})
				}
			}
		}
		return false
	}

	// The answer is at least both corner heights and at most the highest floor.
	low, high := max(grid[0][0], grid[n-1][n-1]), n*n-1
	for low < high {
		middle := (low + high) / 2
		if reachable(middle) {
			high = middle
		} else {
			low = middle + 1
		}
	}
	return low
}
