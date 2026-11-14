class Solution {
    fun maximalSquare(matrix: Array<CharArray>): Int {
        val columns = matrix[0].size
        // side[c + 1] is the largest square ending at column c of the current row (before the
        // update: of the row above); side[0] is a border of zeros.
        val side = IntArray(columns + 1)
        var best = 0
        for (row in matrix) {
            var diagonal = 0 // the row-above value of the previous column, saved before it is overwritten
            for (c in 1..columns) {
                val above = side[c]
                side[c] = if (row[c - 1] == '1') 1 + minOf(above, side[c - 1], diagonal) else 0
                best = maxOf(best, side[c])
                diagonal = above
            }
        }
        return best * best
    }
}
