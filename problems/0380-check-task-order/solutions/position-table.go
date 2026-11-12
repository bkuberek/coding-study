package check_task_order

func isValidTaskOrder(n int, prerequisites [][]int, order []int) bool {
	if len(order) != n {
		return false
	}
	// position[t]: where task t stands in the order, or -1 while it has not been seen.
	position := make([]int, n)
	for task := range position {
		position[task] = -1
	}
	for place, task := range order {
		if position[task] != -1 {
			return false
		}
		position[task] = place
	}
	for _, pair := range prerequisites {
		if position[pair[0]] >= position[pair[1]] {
			return false
		}
	}
	return true
}
