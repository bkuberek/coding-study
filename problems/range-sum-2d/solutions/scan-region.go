package range_sum_2d

type NumMatrix struct {
	matrix [][]int
}

func NewNumMatrix(matrix [][]int) *NumMatrix {
	return &NumMatrix{matrix: matrix}
}

func (m *NumMatrix) SumRegion(row1 int, col1 int, row2 int, col2 int) int {
	total := 0
	for _, cells := range m.matrix[row1 : row2+1] {
		for _, value := range cells[col1 : col2+1] {
			total += value
		}
	}
	return total
}
