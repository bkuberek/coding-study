package product_except_self

import "slices"

func productExceptSelf(nums []int) []int {
	n := len(nums)
	answer := slices.Repeat([]int{1}, n)
	for i := 1; i < n; i++ {
		answer[i] = answer[i-1] * nums[i-1] // product of nums[:i]
	}
	after := 1 // product of nums[i+1:]
	for i := n - 1; i >= 0; i-- {
		answer[i] *= after
		after *= nums[i]
	}
	return answer
}
