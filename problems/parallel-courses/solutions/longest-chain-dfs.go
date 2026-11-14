package parallel_courses

const onPath = -1 // marks a course whose chain length is still being computed

func minimumSemesters(n int, relations [][]int) int {
	required := make([][]int, n+1)
	for _, relation := range relations {
		before, after := relation[0], relation[1]
		required[after] = append(required[after], before)
	}
	// chain[c]: courses on the longest prerequisite chain ending at c; 0 = not computed yet.
	chain := make([]int, n+1)

	// chainLength returns the longest chain ending at course, or -1 if its prerequisites loop.
	var chainLength func(course int) int
	chainLength = func(course int) int {
		if chain[course] == onPath {
			return -1
		}
		if chain[course] > 0 {
			return chain[course]
		}
		chain[course] = onPath
		longest := 0
		for _, before := range required[course] {
			length := chainLength(before)
			if length < 0 {
				return -1
			}
			longest = max(longest, length)
		}
		chain[course] = longest + 1
		return chain[course]
	}

	semesters := 0
	for course := 1; course <= n; course++ {
		length := chainLength(course)
		if length < 0 {
			return -1
		}
		semesters = max(semesters, length)
	}
	return semesters
}
