package min_meeting_rooms

import "slices"

func minMeetingRooms(intervals [][]int) int {
	starts := make([]int, len(intervals))
	ends := make([]int, len(intervals))
	for i, interval := range intervals {
		starts[i], ends[i] = interval[0], interval[1]
	}
	slices.Sort(starts)
	slices.Sort(ends)
	rooms, ended := 0, 0
	for _, start := range starts {
		if ends[ended] <= start {
			// Some meeting has ended by now: its room is reused.
			ended++
		} else {
			rooms++
		}
	}
	return rooms
}
