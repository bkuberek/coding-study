package first_missing_positive

func firstMissingPositive(nums []int) int {
	n := len(nums)
	for i := 0; i < n; i++ {
		// Swap nums[i] to its home index nums[i]-1 until the value here has no home in
		// range or its home already holds it. Every swap settles one value for good.
		for nums[i] >= 1 && nums[i] <= n && nums[nums[i]-1] != nums[i] {
			home := nums[i] - 1
			nums[i], nums[home] = nums[home], nums[i]
		}
	}
	for i, value := range nums {
		if value != i+1 {
			return i + 1
		}
	}
	return n + 1
}
