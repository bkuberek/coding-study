package sum_of_subarray_minimums

const mod = 1_000_000_007

func sumSubarrayMins(arr []int) int {
	// ending[i] is the sum of the minimums of the subarrays that end at i.
	ending := make([]int, len(arr))
	// Indexes whose values strictly increase from bottom to top.
	var stack []int
	total := 0
	for index, value := range arr {
		for len(stack) > 0 && arr[stack[len(stack)-1]] >= value {
			stack = stack[:len(stack)-1]
		}
		if len(stack) > 0 {
			previous := stack[len(stack)-1]
			// Starts after the previous smaller element have minimum value; earlier starts
			// have the same minimums as the subarrays ending at previous.
			ending[index] = ending[previous] + value*(index-previous)
		} else {
			ending[index] = value * (index + 1)
		}
		stack = append(stack, index)
		total += ending[index]
	}
	return total % mod
}
