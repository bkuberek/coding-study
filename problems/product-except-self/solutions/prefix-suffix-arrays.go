package product_except_self

import "slices"

func productExceptSelf(nums []int) []int {
	n := len(nums)
	left := slices.Repeat([]int{1}, n) // left[i] is the product of nums[:i]
	for i := 1; i < n; i++ {
		left[i] = left[i-1] * nums[i-1]
	}
	right := slices.Repeat([]int{1}, n) // right[i] is the product of nums[i+1:]
	for i := n - 2; i >= 0; i-- {
		right[i] = right[i+1] * nums[i+1]
	}
	answer := make([]int, n)
	for i := range answer {
		answer[i] = left[i] * right[i]
	}
	return answer
}
