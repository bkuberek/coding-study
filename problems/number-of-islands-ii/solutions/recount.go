package number_of_islands_ii

var steps = [4][2]int{{1, 0}, {-1, 0}, {0, 1}, {0, -1}}

func numIslands2(m int, n int, positions [][]int) []int {
	land := make([][]bool, m)
	for r := range land {
		land[r] = make([]bool, n)
	}
	var cells [][2]int // every land cell, each once

	countIslands := func() int {
		seen := make(map[[2]int]bool)
		islands := 0
		for _, start := range cells {
			if seen[start] {
				continue
			}
			islands++
			seen[start] = true
			stack := [][2]int{start}
			for len(stack) > 0 {
				cell := stack[len(stack)-1]
				stack = stack[:len(stack)-1]
				for _, step := range steps {
					nr, nc := cell[0]+step[0], cell[1]+step[1]
					next := [2]int{nr, nc}
					if nr >= 0 && nr < m && nc >= 0 && nc < n && land[nr][nc] && !seen[next] {
						seen[next] = true
						stack = append(stack, next)
					}
				}
			}
		}
		return islands
	}

	counts := make([]int, 0, len(positions))
	for _, position := range positions {
		r, c := position[0], position[1]
		if !land[r][c] {
			land[r][c] = true
			cells = append(cells, [2]int{r, c})
		}
		counts = append(counts, countIslands())
	}
	return counts
}
