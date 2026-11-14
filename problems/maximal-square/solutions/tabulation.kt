class Solution {
    fun maximalSquare(matrix: Array<CharArray>): Int {
        // side[r + 1][c + 1] is the largest all-ones square with its bottom-right corner at (r, c);
        // row 0 and column 0 are a border of zeros.
        val side = Array(matrix.size + 1) { IntArray(matrix[0].size + 1) }
        var best = 0
        for ((r, row) in matrix.withIndex()) {
            for ((c, cell) in row.withIndex()) {
                if (cell == '1') {
                    side[r + 1][c + 1] = 1 + minOf(side[r][c + 1], side[r + 1][c], side[r][c])
                    best = maxOf(best, side[r + 1][c + 1])
                }
            }
        }
        return best * best
    }
}
