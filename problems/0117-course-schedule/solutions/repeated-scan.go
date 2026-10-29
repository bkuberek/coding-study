package course_schedule

func canFinish(numCourses int, prerequisites [][]int) bool {
	required := make([][]int, numCourses)
	for _, pair := range prerequisites {
		course, before := pair[0], pair[1]
		required[course] = append(required[course], before)
	}
	taken := make([]bool, numCourses)
	for round := 0; round < numCourses; round++ {
		// Take the first course whose prerequisites are all done; give up if there is none.
		found := false
		for course := 0; course < numCourses && !found; course++ {
			if !taken[course] && allTaken(required[course], taken) {
				taken[course] = true
				found = true
			}
		}
		if !found {
			return false
		}
	}
	return true
}

func allTaken(courses []int, taken []bool) bool {
	for _, course := range courses {
		if !taken[course] {
			return false
		}
	}
	return true
}
