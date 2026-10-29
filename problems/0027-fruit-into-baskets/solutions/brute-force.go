package fruit_into_baskets

const empty = -1 // marks an unused basket; fruit types are never negative

func totalFruit(fruits []int) int {
	best := 0
	for start := range fruits {
		first, second := fruits[start], empty
		end := start
		for end < len(fruits) {
			fruit := fruits[end]
			if fruit != first && fruit != second {
				if second != empty {
					break
				}
				second = fruit
			}
			end++
		}
		best = max(best, end-start)
	}
	return best
}
