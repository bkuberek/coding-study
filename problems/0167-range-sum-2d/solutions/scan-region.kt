class NumMatrix(private val matrix: Array<IntArray>) {
    fun sumRegion(row1: Int, col1: Int, row2: Int, col2: Int): Int {
        var total = 0
        for (row in row1..row2) {
            val cells = matrix[row]
            for (col in col1..col2) {
                total += cells[col]
            }
        }
        return total
    }
}
