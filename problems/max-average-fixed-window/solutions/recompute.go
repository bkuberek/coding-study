package max_average_fixed_window

import "math"

func maxWindowAverage(nums []int, k int) float64 {
	best := math.Inf(-1)
	for start := 0; start+k <= len(nums); start++ {
		sum := 0
		for _, value := range nums[start : start+k] {
			sum += value
		}
		best = math.Max(best, float64(sum)/float64(k))
	}
	return best
}
