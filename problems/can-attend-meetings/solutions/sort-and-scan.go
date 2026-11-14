package can_attend_meetings

import (
	"cmp"
	"slices"
)

func canAttendMeetings(intervals [][]int) bool {
	ordered := slices.Clone(intervals)
	slices.SortFunc(ordered, func(a, b []int) int { return cmp.Compare(a[0], b[0]) })
	// After sorting by start, only neighbors can be the first clash.
	for i := 1; i < len(ordered); i++ {
		if ordered[i-1][1] > ordered[i][0] {
			return false
		}
	}
	return true
}
