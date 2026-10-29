package min_interval_per_query

import (
	"cmp"
	"slices"
	"sort"
)

func minInterval(intervals [][]int, queries []int) []int {
	points := slices.Clone(queries)
	slices.Sort(points)
	points = slices.Compact(points)
	sizeAt := make([]int, len(points))
	for i := range sizeAt {
		sizeAt[i] = -1
	}
	// nextOpen[k]: a link toward the first point at or after k without an answer yet;
	// len(points) is a sentinel meaning "none left".
	nextOpen := make([]int, len(points)+1)
	for i := range nextOpen {
		nextOpen[i] = i
	}
	firstOpen := func(k int) int {
		root := k
		for nextOpen[root] != root {
			root = nextOpen[root]
		}
		for nextOpen[k] != root {
			nextOpen[k], k = root, nextOpen[k]
		}
		return root
	}

	bySize := slices.Clone(intervals)
	slices.SortStableFunc(bySize, func(a, b []int) int { return cmp.Compare(a[1]-a[0], b[1]-b[0]) })
	for _, interval := range bySize {
		left, right := interval[0], interval[1]
		k := firstOpen(sort.SearchInts(points, left))
		for k < len(points) && points[k] <= right {
			sizeAt[k] = right - left + 1
			nextOpen[k] = k + 1
			k = firstOpen(k + 1)
		}
	}
	position := make(map[int]int, len(points))
	for k, point := range points {
		position[point] = k
	}
	answer := make([]int, len(queries))
	for i, query := range queries {
		answer[i] = sizeAt[position[query]]
	}
	return answer
}
