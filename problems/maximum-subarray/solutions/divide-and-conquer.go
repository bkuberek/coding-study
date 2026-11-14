package maximum_subarray

func maxSubArray(nums []int) int {
	// The best subarray sum within nums[low..high] (inclusive).
	var bestIn func(low, high int) int
	bestIn = func(low, high int) int {
		if low == high {
			return nums[low]
		}
		middle := (low + high) / 2
		// The best crossing subarray is a best suffix of the left half plus a best prefix of
		// the right half.
		leftSuffix, total := nums[middle], 0
		for i := middle; i >= low; i-- {
			total += nums[i]
			leftSuffix = max(leftSuffix, total)
		}
		rightPrefix, total := nums[middle+1], 0
		for i := middle + 1; i <= high; i++ {
			total += nums[i]
			rightPrefix = max(rightPrefix, total)
		}
		return max(bestIn(low, middle), bestIn(middle+1, high), leftSuffix+rightPrefix)
	}
	return bestIn(0, len(nums)-1)
}
