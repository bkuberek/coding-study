package can_attend_meetings

func canAttendMeetings(intervals [][]int) bool {
	for i, first := range intervals {
		for _, second := range intervals[i+1:] {
			// Half-open meetings share a moment exactly when each starts before the other ends.
			if first[0] < second[1] && second[0] < first[1] {
				return false
			}
		}
	}
	return true
}
