package daily_temperatures

func dailyTemperatures(temperatures []int) []int {
	days := len(temperatures)
	waits := make([]int, days) // 0 stays for a day with no warmer day after it
	for day := 0; day < days; day++ {
		for later := day + 1; later < days; later++ {
			if temperatures[later] > temperatures[day] {
				waits[day] = later - day
				break
			}
		}
	}
	return waits
}
