package median_of_two_sorted_arrays

import "math"

func findMedianSortedArrays(nums1 []int, nums2 []int) float64 {
	shorter, longer := nums1, nums2
	if len(shorter) > len(longer) {
		shorter, longer = longer, shorter
	}
	total := len(shorter) + len(longer)
	lowerSize := (total + 1) / 2
	low, high := 0, len(shorter)
	for low <= high {
		// Take takeShort values from shorter and the rest of the lower half from longer.
		takeShort := low + (high-low)/2
		takeLong := lowerSize - takeShort
		shortLeft, shortRight := neighbors(shorter, takeShort)
		longLeft, longRight := neighbors(longer, takeLong)
		switch {
		case shortLeft > longRight:
			high = takeShort - 1
		case longLeft > shortRight:
			low = takeShort + 1
		default:
			lowerMax := max(shortLeft, longLeft)
			if total%2 == 1 {
				return float64(lowerMax)
			}
			return float64(lowerMax+min(shortRight, longRight)) / 2
		}
	}
	panic("the arrays must be sorted")
}

// neighbors returns the values just before and just after a cut at position cut, using
// math.MinInt and math.MaxInt where the cut has no neighbor on that side.
func neighbors(nums []int, cut int) (left, right int) {
	left, right = math.MinInt, math.MaxInt
	if cut > 0 {
		left = nums[cut-1]
	}
	if cut < len(nums) {
		right = nums[cut]
	}
	return left, right
}
