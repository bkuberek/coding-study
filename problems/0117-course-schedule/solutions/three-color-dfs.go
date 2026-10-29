package course_schedule

const (
	unvisited = iota
	onPath
	done
)

func canFinish(numCourses int, prerequisites [][]int) bool {
	required := make([][]int, numCourses)
	for _, pair := range prerequisites {
		course, before := pair[0], pair[1]
		required[course] = append(required[course], before)
	}
	state := make([]int, numCourses)

	// completes reports whether every prerequisite chain below course ends without looping.
	var completes func(course int) bool
	completes = func(course int) bool {
		state[course] = onPath
		for _, before := range required[course] {
			if state[before] == onPath {
				return false // the chain came back to a course still being explored
			}
			if state[before] == unvisited && !completes(before) {
				return false
			}
		}
		state[course] = done
		return true
	}

	for course := 0; course < numCourses; course++ {
		if state[course] != done && !completes(course) {
			return false
		}
	}
	return true
}
