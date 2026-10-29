package container_with_most_water

func maxArea(height []int) int {
	left, right := 0, len(height)-1
	best := 0
	for left < right {
		width := right - left
		if height[left] < height[right] {
			best = max(best, width*height[left])
			left++
		} else {
			best = max(best, width*height[right])
			right--
		}
	}
	return best
}
