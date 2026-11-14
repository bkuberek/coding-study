package trapping_rain_water

func trap(height []int) int {
	n := len(height)
	leftMax := make([]int, n) // leftMax[i] is the tallest bar in height[:i+1]
	tallest := 0
	for i, bar := range height {
		tallest = max(tallest, bar)
		leftMax[i] = tallest
	}
	rightMax := make([]int, n) // rightMax[i] is the tallest bar in height[i:]
	tallest = 0
	for i := n - 1; i >= 0; i-- {
		tallest = max(tallest, height[i])
		rightMax[i] = tallest
	}
	water := 0
	for i, bar := range height {
		water += min(leftMax[i], rightMax[i]) - bar
	}
	return water
}
