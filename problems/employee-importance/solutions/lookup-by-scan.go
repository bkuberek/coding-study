package employee_importance

func getImportance(employees [][]int, employeeId int) int {
	total := 0
	pending := []int{employeeId}
	for len(pending) > 0 {
		wanted := pending[len(pending)-1]
		pending = pending[:len(pending)-1]
		for _, record := range employees {
			if record[0] == wanted {
				total += record[1]
				pending = append(pending, record[2:]...)
				break
			}
		}
	}
	return total
}
