package range_sum_2d

type NumMatrix struct {
	prefix [][]int
}

func NewNumMatrix(matrix [][]int) *NumMatrix {
	cols := len(matrix[0])
	// prefix[r][c] is the sum of the sub-grid matrix[:r][:c]; row 0 and column 0 are zeros.
	prefix := make([][]int, len(matrix)+1)
	prefix[0] = make([]int, cols+1)
	for r, cells := range matrix {
		above := prefix[r]
		row := make([]int, cols+1)
		running := 0
		for c, value := range cells {
			running += value
			row[c+1] = above[c+1] + running
		}
		prefix[r+1] = row
	}
	return &NumMatrix{prefix: prefix}
}

func (m *NumMatrix) SumRegion(row1 int, col1 int, row2 int, col2 int) int {
	p := m.prefix
	return p[row2+1][col2+1] - p[row1][col2+1] - p[row2+1][col1] + p[row1][col1]
}
