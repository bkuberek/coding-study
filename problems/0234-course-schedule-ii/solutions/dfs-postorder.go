package course_schedule_ii

const (
	unseen = iota
	active
	done
)

func findOrder(numCourses int, prerequisites [][]int) []int {
	required := make([][]int, numCourses)
	for _, pair := range prerequisites {
		required[pair[0]] = append(required[pair[0]], pair[1])
	}
	state := make([]int, numCourses)
	cursor := make([]int, numCourses) // index of the next prerequisite to visit, per course
	order := make([]int, 0, numCourses)
	for root := 0; root < numCourses; root++ {
		if state[root] != unseen {
			continue
		}
		state[root] = active
		stack := []int{root}
		for len(stack) > 0 {
			course := stack[len(stack)-1]
			if cursor[course] == len(required[course]) {
				// Every prerequisite is already in the order: the course can follow them.
				stack = stack[:len(stack)-1]
				state[course] = done
				order = append(order, course)
				continue
			}
			before := required[course][cursor[course]]
			cursor[course]++
			if state[before] == active {
				return []int{} // the path loops back to a course still being explored
			}
			if state[before] == unseen {
				state[before] = active
				stack = append(stack, before)
			}
		}
	}
	return order
}
