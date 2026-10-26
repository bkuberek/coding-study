class Solution {
    fun burnTimes(grid: Array<IntArray>): Array<IntArray> {
        val rows = grid.size
        val cols = grid[0].size
        val times = Array(rows) { IntArray(cols) { -1 } }
        val queue = ArrayDeque<Pair<Int, Int>>()
        for (r in 0 until rows) {
            for (c in 0 until cols) {
                if (grid[r][c] == 2) {
                    times[r][c] = 0
                    queue.addLast(r to c)
                }
            }
        }
        while (queue.isNotEmpty()) {
            val (r, c) = queue.removeFirst()
            for ((dr, dc) in STEPS) {
                val nr = r + dr
                val nc = c + dc
                if (nr in 0 until rows && nc in 0 until cols &&
                    grid[nr][nc] == 1 && times[nr][nc] == -1
                ) {
                    times[nr][nc] = times[r][c] + 1
                    queue.addLast(nr to nc)
                }
            }
        }
        return times
    }

    private companion object {
        val STEPS = listOf(1 to 0, -1 to 0, 0 to 1, 0 to -1)
    }
}
