class Solution {
    fun maximalRectangle(matrix: Array<CharArray>): Int {
        val rows = matrix.size
        val columns = matrix[0].size
        // width[r][c] is the number of consecutive ones ending at (r, c) in row r.
        val width = Array(rows) { IntArray(columns) }
        var best = 0
        for (r in 0 until rows) {
            for (c in 0 until columns) {
                if (matrix[r][c] == '0') continue
                width[r][c] = if (c > 0) width[r][c - 1] + 1 else 1
                // Rectangles with bottom-right corner (r, c): extend upwards one row at a time;
                // the rectangle is as wide as the narrowest row it spans.
                var narrowest = width[r][c]
                var top = r
                while (top >= 0 && narrowest > 0) {
                    narrowest = minOf(narrowest, width[top][c])
                    best = maxOf(best, narrowest * (r - top + 1))
                    top--
                }
            }
        }
        return best
    }
}
