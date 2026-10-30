package count_smaller_after_self

func countSmaller(nums []int) []int {
	n := len(nums)
	counts := make([]int, n)
	order := make([]int, n) // positions, sorted by value within each merged run
	for i := range order {
		order[i] = i
	}
	buffer := make([]int, n)
	// Bottom-up merge sort of positions by value; no recursion needed.
	for width := 1; width < n; width *= 2 {
		for low := 0; low < n; low += 2 * width {
			middle := min(low+width, n)
			high := min(low+2*width, n)
			left, right, out := low, middle, low
			for left < middle {
				if right < high && nums[order[right]] < nums[order[left]] {
					buffer[out] = order[right]
					right++
				} else {
					// Every right-half element taken so far is smaller and came after it.
					counts[order[left]] += right - middle
					buffer[out] = order[left]
					left++
				}
				out++
			}
			copy(buffer[out:high], order[right:high])
		}
		order, buffer = buffer, order
	}
	return counts
}
