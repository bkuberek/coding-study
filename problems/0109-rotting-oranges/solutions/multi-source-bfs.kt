private const val FRESH = 1
private const val ROTTEN = 2

class Solution {
    fun orangesRotting(grid: Array<IntArray>): Int {
        val rows = grid.size
        val cols = grid[0].size
        val queue = ArrayDeque<Int>()
        var fresh = 0
        for (r in 0 until rows) {
            for (c in 0 until cols) {
                when (grid[r][c]) {
                    ROTTEN -> queue.addLast(r * cols + c)
                    FRESH -> fresh++
                }
            }
        }
        var minutes = 0
        // Each pass of the outer loop rots the whole current frontier: one minute.
        while (queue.isNotEmpty() && fresh > 0) {
            minutes++
            repeat(queue.size) {
                val cell = queue.removeFirst()
                val r = cell / cols
                val c = cell % cols
                for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                    if (nr in 0 until rows && nc in 0 until cols && grid[nr][nc] == FRESH) {
                        grid[nr][nc] = ROTTEN
                        fresh--
                        queue.addLast(nr * cols + nc)
                    }
                }
            }
        }
        return if (fresh == 0) minutes else -1
    }
}
