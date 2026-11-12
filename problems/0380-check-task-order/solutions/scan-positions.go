package check_task_order

func isValidTaskOrder(n int, prerequisites [][]int, order []int) bool {
	if len(order) != n {
		return false
	}
	for task := 0; task < n; task++ {
		if occurrences(order, task) != 1 {
			return false
		}
	}
	for _, pair := range prerequisites {
		if indexOf(order, pair[0]) >= indexOf(order, pair[1]) {
			return false
		}
	}
	return true
}

func occurrences(order []int, task int) int {
	count := 0
	for _, listed := range order {
		if listed == task {
			count++
		}
	}
	return count
}

func indexOf(order []int, task int) int {
	for place, listed := range order {
		if listed == task {
			return place
		}
	}
	return -1
}
