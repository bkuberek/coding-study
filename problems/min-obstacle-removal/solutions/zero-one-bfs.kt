class Solution {
    fun minimumObstacles(grid: Array<IntArray>): Int {
        val rows = grid.size
        val cols = grid[0].size
        val removals = Array(rows) { IntArray(cols) { Int.MAX_VALUE } }
        removals[0][0] = 0
        // The deque stays sorted by removals: zero-cost steps go to the front, one-cost steps
        // to the back, so its two ends never differ by more than one.
        val deque = ArrayDeque<Int>()
        deque.addLast(0)
        while (deque.isNotEmpty()) {
            val cell = deque.removeFirst()
            val r = cell / cols
            val c = cell % cols
            val cost = removals[r][c]
            if (r == rows - 1 && c == cols - 1) return cost
            for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                if (nr !in 0 until rows || nc !in 0 until cols) continue
                val offered = cost + grid[nr][nc]
                if (offered < removals[nr][nc]) {
                    removals[nr][nc] = offered
                    if (grid[nr][nc] == 0) deque.addFirst(nr * cols + nc) else deque.addLast(nr * cols + nc)
                }
            }
        }
        return removals[rows - 1][cols - 1]
    }
}
