package sum_of_subarray_minimums

const mod = 1_000_000_007

func sumSubarrayMins(arr []int) int {
	total := 0
	for start := range arr {
		// Extend the subarray one element at a time, keeping its running minimum.
		lowest := arr[start]
		for _, value := range arr[start:] {
			lowest = min(lowest, value)
			total += lowest
		}
		total %= mod
	}
	return total
}
