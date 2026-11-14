package sorting_workbench

import (
	"container/heap"
	"slices"
)

// SortingWorkbench holds four classic sorts, each written the way the statement specifies it,
// and a meter that counts the work of the latest sort. A sort returns a new slice and never
// changes its input.
type SortingWorkbench struct {
	meter            []int
	mergeComparisons int
}

func NewSortingWorkbench() *SortingWorkbench {
	return &SortingWorkbench{}
}

// Level 1
func (w *SortingWorkbench) InsertionSort(values []int) []int {
	items := slices.Clone(values)
	comparisons, moves := 0, 0
	for i := 1; i < len(items); i++ {
		key := items[i]
		j := i - 1
		for j >= 0 {
			comparisons++
			if items[j] <= key {
				break
			}
			items[j+1] = items[j]
			moves++
			j--
		}
		items[j+1] = key
	}
	w.meter = []int{comparisons, moves}
	return items
}

func (w *SortingWorkbench) Report() []int {
	return slices.Clone(w.meter)
}

// Level 2
func (w *SortingWorkbench) MergeSortBy(rows [][]int, key int) [][]int {
	w.mergeComparisons = 0
	merged := w.mergeSort(rows, key)
	w.meter = []int{w.mergeComparisons}
	result := make([][]int, len(merged))
	for i, row := range merged {
		result[i] = slices.Clone(row)
	}
	return result
}

func (w *SortingWorkbench) mergeSort(rows [][]int, key int) [][]int {
	if len(rows) <= 1 {
		return slices.Clone(rows)
	}
	middle := len(rows) / 2
	left := w.mergeSort(rows[:middle], key)
	right := w.mergeSort(rows[middle:], key)
	merged := make([][]int, 0, len(rows))
	i, j := 0, 0
	for i < len(left) && j < len(right) {
		w.mergeComparisons++
		if left[i][key] <= right[j][key] {
			merged = append(merged, left[i])
			i++
		} else {
			merged = append(merged, right[j])
			j++
		}
	}
	merged = append(merged, left[i:]...)
	return append(merged, right[j:]...)
}

// Level 3
func (w *SortingWorkbench) QuickSort(values []int) []int {
	items := slices.Clone(values)
	calls, steps := 0, 0
	ranges := [][2]int{{0, len(items) - 1}}
	for len(ranges) > 0 {
		span := ranges[len(ranges)-1]
		ranges = ranges[:len(ranges)-1]
		low, high := span[0], span[1]
		if high-low < 1 {
			continue
		}
		below, above := partition(items, low, high)
		calls++
		steps += high - low + 1
		ranges = append(ranges, [2]int{low, below - 1}, [2]int{above + 1, high})
	}
	w.meter = []int{calls, steps}
	return items
}

func (w *SortingWorkbench) QuickSelect(values []int, k int) int {
	items := slices.Clone(values)
	target := k - 1
	calls, steps := 0, 0
	low, high := 0, len(items)-1
	for low < high {
		below, above := partition(items, low, high)
		calls++
		steps += high - low + 1
		if target < below {
			high = below - 1
		} else if target > above {
			low = above + 1
		} else {
			break
		}
	}
	w.meter = []int{calls, steps}
	return items[target]
}

// partition leaves items[low:below] < pivot, items[below:above+1] == pivot and items[above+1:high+1] > pivot.
func partition(items []int, low, high int) (int, int) {
	pivot := items[low+(high-low)/2]
	below, i, above := low, low, high
	for i <= above {
		switch {
		case items[i] < pivot:
			items[below], items[i] = items[i], items[below]
			below++
			i++
		case items[i] > pivot:
			items[i], items[above] = items[above], items[i]
			above--
		default:
			i++
		}
	}
	return below, above
}

// Level 4
func (w *SortingWorkbench) ExternalSort(values []int, memory int, ways int) []int {
	var runs [][]int
	for start := 0; start < len(values); start += memory {
		run := slices.Clone(values[start:min(start+memory, len(values))])
		slices.Sort(run)
		runs = append(runs, run)
	}
	initialRuns, passes := len(runs), 0
	for len(runs) > 1 {
		var next [][]int
		for start := 0; start < len(runs); start += ways {
			next = append(next, mergeGroup(runs[start:min(start+ways, len(runs))]))
		}
		runs = next
		passes++
	}
	w.meter = []int{initialRuns, passes}
	if len(runs) == 0 {
		return []int{}
	}
	return runs[0]
}

// front is the next unread value of one run of the group being merged.
type front struct {
	value, run, position int
}

// fronts is a min-heap that holds the front value of each run, ties broken by run.
type fronts []front

func (h fronts) Len() int { return len(h) }
func (h fronts) Less(a, b int) bool {
	if h[a].value != h[b].value {
		return h[a].value < h[b].value
	}
	return h[a].run < h[b].run
}
func (h fronts) Swap(a, b int) { h[a], h[b] = h[b], h[a] }
func (h *fronts) Push(x any)   { *h = append(*h, x.(front)) }
func (h *fronts) Pop() any {
	old := *h
	last := old[len(old)-1]
	*h = old[:len(old)-1]
	return last
}

func mergeGroup(group [][]int) []int {
	pending := &fronts{}
	total := 0
	for index, run := range group {
		*pending = append(*pending, front{run[0], index, 0})
		total += len(run)
	}
	heap.Init(pending)
	merged := make([]int, 0, total)
	for pending.Len() > 0 {
		next := heap.Pop(pending).(front)
		merged = append(merged, next.value)
		run := group[next.run]
		if next.position+1 < len(run) {
			heap.Push(pending, front{run[next.position+1], next.run, next.position + 1})
		}
	}
	return merged
}
