private const val FRESH = 1
private const val ROTTEN = 2

class Solution {
    fun orangesRotting(grid: Array<IntArray>): Int {
        val rows = grid.size
        val cols = grid[0].size
        fun touchesRot(r: Int, c: Int): Boolean =
            (r > 0 && grid[r - 1][c] == ROTTEN) ||
                (r + 1 < rows && grid[r + 1][c] == ROTTEN) ||
                (c > 0 && grid[r][c - 1] == ROTTEN) ||
                (c + 1 < cols && grid[r][c + 1] == ROTTEN)

        var minutes = 0
        while (true) {
            // Collect this minute's changes before applying any, so new rot waits a minute.
            val turning = (0 until rows).flatMap { r ->
                (0 until cols).filter { c -> grid[r][c] == FRESH && touchesRot(r, c) }.map { c -> r to c }
            }
            if (turning.isEmpty()) break
            for ((r, c) in turning) grid[r][c] = ROTTEN
            minutes++
        }
        return if (grid.any { row -> FRESH in row }) -1 else minutes
    }
}
