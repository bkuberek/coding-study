package count_smaller_after_self

import "slices"

func countSmaller(nums []int) []int {
	// Coordinate compression: rank 1 is the smallest distinct value.
	distinct := slices.Clone(nums)
	slices.Sort(distinct)
	distinct = slices.Compact(distinct)
	size := len(distinct)
	tree := make([]int, size+1) // Fenwick tree: how many seen values have each rank
	counts := make([]int, len(nums))
	for i := len(nums) - 1; i >= 0; i-- {
		position, _ := slices.BinarySearch(distinct, nums[i])
		rank := position + 1
		// Seen values with a rank below rank, i.e. strictly smaller values to the right.
		smaller := 0
		for j := rank - 1; j > 0; j -= j & -j {
			smaller += tree[j]
		}
		counts[i] = smaller
		for ; rank <= size; rank += rank & -rank {
			tree[rank]++
		}
	}
	return counts
}
