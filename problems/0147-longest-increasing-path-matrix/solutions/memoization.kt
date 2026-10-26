private val STEPS = arrayOf(1 to 0, -1 to 0, 0 to 1, 0 to -1)

class Solution {
    fun longestIncreasingPath(matrix: Array<IntArray>): Int {
        val rows = matrix.size
        val columns = matrix[0].size
        // longest[r][c] caches the longest increasing path that starts at (r, c); 0 is unknown.
        val longest = Array(rows) { IntArray(columns) }

        fun explore(r: Int, c: Int): Int {
            if (longest[r][c] == 0) {
                var best = 1
                for ((dr, dc) in STEPS) {
                    val nr = r + dr
                    val nc = c + dc
                    if (nr in 0 until rows && nc in 0 until columns && matrix[nr][nc] > matrix[r][c]) {
                        best = maxOf(best, 1 + explore(nr, nc))
                    }
                }
                longest[r][c] = best
            }
            return longest[r][c]
        }

        var answer = 0
        for (r in 0 until rows) {
            for (c in 0 until columns) {
                answer = maxOf(answer, explore(r, c))
            }
        }
        return answer
    }
}
