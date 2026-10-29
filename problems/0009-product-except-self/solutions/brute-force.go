package product_except_self

func productExceptSelf(nums []int) []int {
	answer := make([]int, len(nums))
	for i := range nums {
		product := 1
		for _, value := range nums[:i] {
			product *= value
		}
		for _, value := range nums[i+1:] {
			product *= value
		}
		answer[i] = product
	}
	return answer
}
