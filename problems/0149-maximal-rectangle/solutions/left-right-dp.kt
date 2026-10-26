class Solution {
    fun maximalRectangle(matrix: Array<CharArray>): Int {
        val columns = matrix[0].size
        // For the current row and each column c: height[c] consecutive ones end here in column c,
        // and the rectangle of that height through column c spans columns left[c] .. right[c] - 1.
        val height = IntArray(columns)
        val left = IntArray(columns)
        val right = IntArray(columns) { columns }
        var best = 0
        for (row in matrix) {
            var boundary = 0 // first column after the last zero seen in this row
            for (c in 0 until columns) {
                if (row[c] == '1') {
                    height[c]++
                    left[c] = maxOf(left[c], boundary)
                } else {
                    height[c] = 0
                    left[c] = 0
                    boundary = c + 1
                }
            }
            boundary = columns // the last zero seen from the right
            for (c in columns - 1 downTo 0) {
                if (row[c] == '1') {
                    right[c] = minOf(right[c], boundary)
                } else {
                    right[c] = columns
                    boundary = c
                }
            }
            for (c in 0 until columns) {
                best = maxOf(best, height[c] * (right[c] - left[c]))
            }
        }
        return best
    }
}
