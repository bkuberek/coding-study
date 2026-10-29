package fruit_into_baskets

func totalFruit(fruits []int) int {
	inWindow := make(map[int]int)
	left, best := 0, 0
	for right, fruit := range fruits {
		inWindow[fruit]++
		for len(inWindow) > 2 {
			leaving := fruits[left]
			inWindow[leaving]--
			if inWindow[leaving] == 0 {
				delete(inWindow, leaving)
			}
			left++
		}
		best = max(best, right-left+1)
	}
	return best
}
