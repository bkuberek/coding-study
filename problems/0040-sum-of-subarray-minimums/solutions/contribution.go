package sum_of_subarray_minimums

const mod = 1_000_000_007

func sumSubarrayMins(arr []int) int {
	total := 0
	// Indexes whose values strictly increase from bottom to top.
	var stack []int
	// One extra step with value 0, below every element, pops whatever is left.
	for index := 0; index <= len(arr); index++ {
		value := 0
		if index < len(arr) {
			value = arr[index]
		}
		for len(stack) > 0 && arr[stack[len(stack)-1]] >= value {
			middle := stack[len(stack)-1]
			stack = stack[:len(stack)-1]
			previous := -1
			if len(stack) > 0 {
				previous = stack[len(stack)-1]
			}
			// Starts after the previous strictly smaller element, ends before the next
			// smaller-or-equal one (index): arr[middle] is the minimum of left * right subarrays.
			left := middle - previous
			right := index - middle
			total += arr[middle] * left * right
		}
		stack = append(stack, index)
	}
	return total % mod
}
