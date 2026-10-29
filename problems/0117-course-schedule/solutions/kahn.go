package course_schedule

func canFinish(numCourses int, prerequisites [][]int) bool {
	unlocks := make([][]int, numCourses)
	waiting := make([]int, numCourses) // prerequisites each course still waits for
	for _, pair := range prerequisites {
		course, before := pair[0], pair[1]
		unlocks[before] = append(unlocks[before], course)
		waiting[course]++
	}
	var ready []int
	for course, count := range waiting {
		if count == 0 {
			ready = append(ready, course)
		}
	}
	taken := 0
	for len(ready) > 0 {
		course := ready[0]
		ready = ready[1:]
		taken++
		for _, unlocked := range unlocks[course] {
			waiting[unlocked]--
			if waiting[unlocked] == 0 {
				ready = append(ready, unlocked)
			}
		}
	}
	// Courses never taken wait, directly or not, on a cycle.
	return taken == numCourses
}
