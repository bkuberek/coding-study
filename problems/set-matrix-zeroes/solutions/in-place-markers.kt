class Solution {
    fun setZeroes(matrix: Array<IntArray>) {
        val rows = matrix.size
        val cols = matrix[0].size
        // matrix[r][0] marks row r (matrix[0][0] marks row 0) and matrix[0][c] marks column c
        // for c >= 1; column 0 needs its own flag, because matrix[0][0] is taken.
        var firstColHasZero = false
        for (r in 0 until rows) {
            if (matrix[r][0] == 0) firstColHasZero = true
            for (c in 1 until cols) {
                if (matrix[r][c] == 0) {
                    matrix[r][0] = 0
                    matrix[0][c] = 0
                }
            }
        }
        // Bottom-up, so the markers in row 0 are read before row 0 itself is cleared.
        for (r in rows - 1 downTo 0) {
            for (c in cols - 1 downTo 1) {
                if (matrix[r][0] == 0 || matrix[0][c] == 0) matrix[r][c] = 0
            }
            if (firstColHasZero) matrix[r][0] = 0
        }
    }
}
