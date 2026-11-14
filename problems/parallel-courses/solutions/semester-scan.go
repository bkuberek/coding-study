package parallel_courses

func minimumSemesters(n int, relations [][]int) int {
	required := make([][]int, n+1)
	for _, relation := range relations {
		before, after := relation[0], relation[1]
		required[after] = append(required[after], before)
	}
	finishedIn := make([]int, n+1) // semester a course was taken in; 0 while not taken
	done, semester := 0, 0
	for done < n {
		semester++
		// Free courses need every prerequisite finished in an earlier semester.
		var free []int
		for course := 1; course <= n; course++ {
			if finishedIn[course] == 0 && allFinishedBefore(required[course], finishedIn, semester) {
				free = append(free, course)
			}
		}
		if len(free) == 0 {
			return -1
		}
		for _, course := range free {
			finishedIn[course] = semester
		}
		done += len(free)
	}
	return semester
}

func allFinishedBefore(courses []int, finishedIn []int, semester int) bool {
	for _, before := range courses {
		if finishedIn[before] == 0 || finishedIn[before] >= semester {
			return false
		}
	}
	return true
}
