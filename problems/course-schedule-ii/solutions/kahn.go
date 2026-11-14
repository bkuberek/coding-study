package course_schedule_ii

func findOrder(numCourses int, prerequisites [][]int) []int {
	unlocks := make([][]int, numCourses)
	waiting := make([]int, numCourses) // prerequisites each course still waits for
	for _, pair := range prerequisites {
		course, before := pair[0], pair[1]
		unlocks[before] = append(unlocks[before], course)
		waiting[course]++
	}
	ready := make([]int, 0, numCourses)
	for course := 0; course < numCourses; course++ {
		if waiting[course] == 0 {
			ready = append(ready, course)
		}
	}
	// ready doubles as the queue and the order: ready[:head] has been taken, the rest is waiting.
	for head := 0; head < len(ready); head++ {
		for _, unlocked := range unlocks[ready[head]] {
			waiting[unlocked]--
			if waiting[unlocked] == 0 {
				ready = append(ready, unlocked)
			}
		}
	}
	// Courses never taken wait, directly or not, on a cycle.
	if len(ready) != numCourses {
		return []int{}
	}
	return ready
}
