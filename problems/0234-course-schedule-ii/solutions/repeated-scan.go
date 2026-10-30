package course_schedule_ii

func findOrder(numCourses int, prerequisites [][]int) []int {
	required := make([][]int, numCourses)
	for _, pair := range prerequisites {
		required[pair[0]] = append(required[pair[0]], pair[1])
	}
	taken := make([]bool, numCourses)
	order := make([]int, 0, numCourses)
	for len(order) < numCourses {
		// Take the first course whose prerequisites are all done; give up if there is none.
		next := -1
		for course := 0; course < numCourses && next < 0; course++ {
			if !taken[course] && allTaken(required[course], taken) {
				next = course
			}
		}
		if next < 0 {
			return []int{}
		}
		taken[next] = true
		order = append(order, next)
	}
	return order
}

func allTaken(courses []int, taken []bool) bool {
	for _, course := range courses {
		if !taken[course] {
			return false
		}
	}
	return true
}
