package trapping_rain_water

func trap(height []int) int {
	left, right := 0, len(height)-1
	leftMax, rightMax := 0, 0
	water := 0
	for left < right {
		if height[left] < height[right] {
			leftMax = max(leftMax, height[left])
			water += leftMax - height[left]
			left++
		} else {
			rightMax = max(rightMax, height[right])
			water += rightMax - height[right]
			right--
		}
	}
	return water
}
