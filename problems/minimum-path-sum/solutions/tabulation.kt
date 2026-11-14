class Solution {
    fun minPathSum(grid: Array<IntArray>): Int {
        val rows = grid.size
        val columns = grid[0].size
        // cheapest[r][c]: the smallest total toll of any route from the top-left block to block (r, c).
        val cheapest = Array(rows) { IntArray(columns) }
        for (row in 0 until rows) {
            for (column in 0 until columns) {
                val arrival = when {
                    row == 0 && column == 0 -> 0
                    row == 0 -> cheapest[row][column - 1]
                    column == 0 -> cheapest[row - 1][column]
                    else -> minOf(cheapest[row - 1][column], cheapest[row][column - 1])
                }
                cheapest[row][column] = arrival + grid[row][column]
            }
        }
        return cheapest[rows - 1][columns - 1]
    }
}
