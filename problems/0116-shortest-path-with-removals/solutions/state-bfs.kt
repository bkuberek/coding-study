class Solution {
    fun shortestPath(grid: Array<IntArray>, k: Int): Int {
        val rows = grid.size
        val cols = grid[0].size
        // A Manhattan route enters at most rows + cols - 3 cells besides the corners, so more
        // removals than that never help.
        val budget = minOf(k, maxOf(0, rows + cols - 3))
        val seen = Array(rows) { Array(cols) { BooleanArray(budget + 1) } }
        seen[0][0][0] = true
        val queue = ArrayDeque<Triple<Int, Int, Int>>()
        queue.addLast(Triple(0, 0, 0))
        var moves = 0
        while (queue.isNotEmpty()) {
            repeat(queue.size) {
                val (r, c, used) = queue.removeFirst()
                if (r == rows - 1 && c == cols - 1) return moves
                for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                    if (nr !in 0 until rows || nc !in 0 until cols) continue
                    val after = used + grid[nr][nc]
                    if (after <= budget && !seen[nr][nc][after]) {
                        seen[nr][nc][after] = true
                        queue.addLast(Triple(nr, nc, after))
                    }
                }
            }
            moves++
        }
        return -1
    }
}
