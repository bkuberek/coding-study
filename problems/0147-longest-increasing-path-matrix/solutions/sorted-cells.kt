private val STEPS = arrayOf(1 to 0, -1 to 0, 0 to 1, 0 to -1)

class Solution {
    fun longestIncreasingPath(matrix: Array<IntArray>): Int {
        val rows = matrix.size
        val columns = matrix[0].size
        // Cells are numbered r * columns + c; longest[cell] is the longest path starting there.
        val longest = IntArray(rows * columns) { 1 }
        // Every larger neighbor comes earlier in decreasing order of value, so its entry is final
        // when the cell is processed. Equal neighbors are never steps, so ties may go either way.
        val order = (0 until rows * columns).sortedByDescending { matrix[it / columns][it % columns] }
        for (cell in order) {
            val r = cell / columns
            val c = cell % columns
            for ((dr, dc) in STEPS) {
                val nr = r + dr
                val nc = c + dc
                if (nr in 0 until rows && nc in 0 until columns && matrix[nr][nc] > matrix[r][c]) {
                    longest[cell] = maxOf(longest[cell], 1 + longest[nr * columns + nc])
                }
            }
        }
        return longest.max()
    }
}
