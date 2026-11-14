package daily_temperatures

func dailyTemperatures(temperatures []int) []int {
	waits := make([]int, len(temperatures))
	// Days still waiting for a warmer day; their readings never rise from bottom to top.
	var waiting []int
	for day, temperature := range temperatures {
		for len(waiting) > 0 && temperatures[waiting[len(waiting)-1]] < temperature {
			earlier := waiting[len(waiting)-1]
			waiting = waiting[:len(waiting)-1]
			waits[earlier] = day - earlier
		}
		waiting = append(waiting, day)
	}
	return waits
}
