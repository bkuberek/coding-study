package trapping_rain_water

import "slices"

func trap(height []int) int {
	water := 0
	for i, bar := range height {
		// Each slices.Max scans a subslice: O(n) work per bar.
		level := min(slices.Max(height[:i+1]), slices.Max(height[i:]))
		water += level - bar
	}
	return water
}
