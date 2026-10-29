package trapping_rain_water

func trap(height []int) int {
	water := 0
	var falling []int // indexes of bars with non-increasing heights
	for right, bar := range height {
		for len(falling) > 0 && height[falling[len(falling)-1]] < bar {
			bottom := height[falling[len(falling)-1]]
			falling = falling[:len(falling)-1]
			if len(falling) == 0 {
				break
			}
			left := falling[len(falling)-1]
			level := min(height[left], bar)
			water += (right - left - 1) * (level - bottom)
		}
		falling = append(falling, right)
	}
	return water
}
