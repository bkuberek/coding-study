package min_meeting_rooms

func minMeetingRooms(intervals [][]int) int {
	// The busiest moment is always the start of some meeting.
	rooms := 0
	for _, moment := range intervals {
		busy := 0
		for _, other := range intervals {
			if other[0] <= moment[0] && moment[0] < other[1] {
				busy++
			}
		}
		rooms = max(rooms, busy)
	}
	return rooms
}
