package range_sum_immutable

type NumArray struct {
	prefix []int64
}

func NewNumArray(nums []int) *NumArray {
	// prefix[i] is the sum of nums[:i]; the leading 0 makes ranges that start at 0 uniform.
	prefix := make([]int64, len(nums)+1)
	for i, value := range nums {
		prefix[i+1] = prefix[i] + int64(value)
	}
	return &NumArray{prefix: prefix}
}

func (a *NumArray) SumRange(left int, right int) int64 {
	return a.prefix[right+1] - a.prefix[left]
}
