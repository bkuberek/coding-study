package time_to_inform_employees

func numOfMinutes(n int, headID int, manager []int, informTime []int) int {
	longest := 0
	for employee := 0; employee < n; employee++ {
		// The news reaches employee after every manager above them has passed it on.
		elapsed := 0
		for current := employee; current != headID; {
			current = manager[current]
			elapsed += informTime[current]
		}
		longest = max(longest, elapsed)
	}
	return longest
}
