package employee_importance

func getImportance(employees [][]int, employeeId int) int {
	byID := make(map[int][]int, len(employees))
	for _, record := range employees {
		byID[record[0]] = record
	}
	total := 0
	pending := []int{employeeId}
	for len(pending) > 0 {
		record := byID[pending[len(pending)-1]]
		pending = pending[:len(pending)-1]
		total += record[1]
		pending = append(pending, record[2:]...)
	}
	return total
}
