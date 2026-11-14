package time_to_inform_employees

func numOfMinutes(n int, headID int, manager []int, informTime []int) int {
	reports := make([][]int, n)
	for employee, boss := range manager {
		if boss != -1 {
			reports[boss] = append(reports[boss], employee)
		}
	}
	type hearing struct{ employee, heardAt int }
	longest := 0
	pending := []hearing{{headID, 0}} // the minute at which each employee hears the news
	for len(pending) > 0 {
		current := pending[len(pending)-1]
		pending = pending[:len(pending)-1]
		longest = max(longest, current.heardAt)
		passedOnAt := current.heardAt + informTime[current.employee]
		for _, report := range reports[current.employee] {
			pending = append(pending, hearing{report, passedOnAt})
		}
	}
	return longest
}
