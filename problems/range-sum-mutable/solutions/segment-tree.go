package range_sum_mutable

type NumArray struct {
	size int
	// Leaves at size .. 2 * size - 1; node i holds the sum of its children 2i and 2i + 1.
	tree []int64
}

func NewNumArray(nums []int) *NumArray {
	size := len(nums)
	tree := make([]int64, 2*size)
	for i, value := range nums {
		tree[size+i] = int64(value)
	}
	for node := size - 1; node > 0; node-- {
		tree[node] = tree[2*node] + tree[2*node+1]
	}
	return &NumArray{size: size, tree: tree}
}

func (a *NumArray) Update(index int, value int) {
	node := index + a.size
	a.tree[node] = int64(value)
	for node > 1 {
		node >>= 1
		a.tree[node] = a.tree[2*node] + a.tree[2*node+1]
	}
}

func (a *NumArray) SumRange(left int, right int) int64 {
	var total int64
	// Half-open [low, high) over the leaves, narrowed one level per round.
	low, high := left+a.size, right+a.size+1
	for low < high {
		if low&1 == 1 {
			total += a.tree[low]
			low++
		}
		if high&1 == 1 {
			high--
			total += a.tree[high]
		}
		low >>= 1
		high >>= 1
	}
	return total
}
