package range_sum_mutable

import "slices"

type NumArray struct {
	nums []int
}

func NewNumArray(nums []int) *NumArray {
	return &NumArray{nums: slices.Clone(nums)}
}

func (a *NumArray) Update(index int, value int) {
	a.nums[index] = value
}

func (a *NumArray) SumRange(left int, right int) int64 {
	var total int64
	for _, value := range a.nums[left : right+1] {
		total += int64(value)
	}
	return total
}
