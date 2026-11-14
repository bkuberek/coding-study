class Solution {
    fun rotate(matrix: Array<IntArray>) {
        val n = matrix.size
        // Reflect across the main diagonal, then mirror every row left to right.
        for (r in 0 until n) {
            for (c in r + 1 until n) {
                val value = matrix[r][c]
                matrix[r][c] = matrix[c][r]
                matrix[c][r] = value
            }
        }
        for (row in matrix) {
            row.reverse()
        }
    }
}
