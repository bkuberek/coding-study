package range_sum_mutable

import "slices"

// lowBit is the lowest set bit of i.
func lowBit(i int) int {
	return i & -i
}

type NumArray struct {
	values []int
	// tree[i] (1-based) holds the sum of the lowBit(i) values ending at position i - 1.
	tree []int64
}

func NewNumArray(nums []int) *NumArray {
	size := len(nums)
	tree := make([]int64, size+1)
	for i := 1; i <= size; i++ {
		tree[i] += int64(nums[i-1])
		if parent := i + lowBit(i); parent <= size {
			tree[parent] += tree[i]
		}
	}
	return &NumArray{values: slices.Clone(nums), tree: tree}
}

func (a *NumArray) Update(index int, value int) {
	delta := int64(value) - int64(a.values[index])
	a.values[index] = value
	for i := index + 1; i < len(a.tree); i += lowBit(i) {
		a.tree[i] += delta
	}
}

func (a *NumArray) SumRange(left int, right int) int64 {
	return a.prefix(right+1) - a.prefix(left)
}

// prefix returns the sum of the first count values.
func (a *NumArray) prefix(count int) int64 {
	var total int64
	for i := count; i > 0; i -= lowBit(i) {
		total += a.tree[i]
	}
	return total
}
