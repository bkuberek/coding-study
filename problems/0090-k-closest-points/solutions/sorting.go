package k_closest_points

import (
	"cmp"
	"slices"
)

func kClosest(points [][]int, k int) [][]int {
	// Squared distances order points exactly like distances, without square roots.
	sorted := slices.Clone(points)
	slices.SortFunc(sorted, func(a, b []int) int {
		return cmp.Compare(squared(a), squared(b))
	})
	return sorted[:k]
}

func squared(point []int) int {
	return point[0]*point[0] + point[1]*point[1]
}
