package parallel_courses

func minimumSemesters(n int, relations [][]int) int {
	unlocks := make([][]int, n+1)
	waiting := make([]int, n+1)
	for _, relation := range relations {
		before, after := relation[0], relation[1]
		unlocks[before] = append(unlocks[before], after)
		waiting[after]++
	}
	var semesterCourses []int
	for course := 1; course <= n; course++ {
		if waiting[course] == 0 {
			semesterCourses = append(semesterCourses, course)
		}
	}
	semesters, taken := 0, 0
	for len(semesterCourses) > 0 {
		semesters++
		taken += len(semesterCourses)
		var nextSemester []int
		for _, course := range semesterCourses {
			for _, unlocked := range unlocks[course] {
				waiting[unlocked]--
				if waiting[unlocked] == 0 {
					nextSemester = append(nextSemester, unlocked)
				}
			}
		}
		semesterCourses = nextSemester
	}
	if taken == n {
		return semesters
	}
	return -1
}
