package container_with_most_water

func maxArea(height []int) int {
	best := 0
	for left := 0; left < len(height)-1; left++ {
		for right := left + 1; right < len(height); right++ {
			water := (right - left) * min(height[left], height[right])
			best = max(best, water)
		}
	}
	return best
}
