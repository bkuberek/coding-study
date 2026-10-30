package range_sum_immutable

type NumArray struct {
	nums []int
}

func NewNumArray(nums []int) *NumArray {
	return &NumArray{nums: nums}
}

func (a *NumArray) SumRange(left int, right int) int64 {
	var total int64
	for _, value := range a.nums[left : right+1] {
		total += int64(value)
	}
	return total
}
