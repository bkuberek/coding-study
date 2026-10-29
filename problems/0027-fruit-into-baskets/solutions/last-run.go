package fruit_into_baskets

const empty = -1 // marks an unused basket; fruit types are never negative

func totalFruit(fruits []int) int {
	best, window := 0, 0
	last, beforeLast := empty, empty
	lastRun := 0
	for _, fruit := range fruits {
		if fruit == last || fruit == beforeLast {
			window++
		} else {
			window = lastRun + 1
		}
		if fruit == last {
			lastRun++
		} else {
			beforeLast, last = last, fruit
			lastRun = 1
		}
		best = max(best, window)
	}
	return best
}
