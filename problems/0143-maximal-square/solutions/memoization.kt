class Solution {
    fun maximalSquare(matrix: Array<CharArray>): Int {
        val rows = matrix.size
        val columns = matrix[0].size
        // side[r][c] caches the largest all-ones square with its top-left corner at (r, c);
        // -1 is unknown.
        val side = Array(rows) { IntArray(columns) { -1 } }

        fun largest(r: Int, c: Int): Int {
            if (r == rows || c == columns || matrix[r][c] == '0') return 0
            if (side[r][c] < 0) {
                side[r][c] = 1 + minOf(largest(r + 1, c), largest(r, c + 1), largest(r + 1, c + 1))
            }
            return side[r][c]
        }

        var best = 0
        for (r in 0 until rows) {
            for (c in 0 until columns) {
                best = maxOf(best, largest(r, c))
            }
        }
        return best * best
    }
}
