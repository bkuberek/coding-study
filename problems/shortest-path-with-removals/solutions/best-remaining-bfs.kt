class Solution {
    fun shortestPath(grid: Array<IntArray>, k: Int): Int {
        val rows = grid.size
        val cols = grid[0].size
        // Enough removals for the straight Manhattan route: nothing can beat it.
        if (k >= rows + cols - 3) return rows + cols - 2
        // best[r][c] is the most removals left with which (r, c) was reached so far.
        val best = Array(rows) { IntArray(cols) { -1 } }
        best[0][0] = k
        val queue = ArrayDeque<Triple<Int, Int, Int>>()
        queue.addLast(Triple(0, 0, k))
        var moves = 0
        while (queue.isNotEmpty()) {
            repeat(queue.size) {
                val (r, c, left) = queue.removeFirst()
                if (r == rows - 1 && c == cols - 1) return moves
                for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                    if (nr !in 0 until rows || nc !in 0 until cols) continue
                    val remaining = left - grid[nr][nc]
                    // A visit that arrives later with no more removals left can never do better.
                    if (remaining > best[nr][nc]) {
                        best[nr][nc] = remaining
                        queue.addLast(Triple(nr, nc, remaining))
                    }
                }
            }
            moves++
        }
        return -1
    }
}
