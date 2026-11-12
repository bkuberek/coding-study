class Solution {
    private val unknown = -1

    fun minPathSum(grid: Array<IntArray>): Int {
        val rows = grid.size
        val columns = grid[0].size
        val cheapest = Array(rows) { IntArray(columns) { unknown } }
        return cheapestTo(grid, cheapest, rows - 1, columns - 1)
    }

    private fun cheapestTo(grid: Array<IntArray>, cheapest: Array<IntArray>, row: Int, column: Int): Int {
        if (cheapest[row][column] != unknown) return cheapest[row][column]
        val arrival = when {
            row == 0 && column == 0 -> 0
            row == 0 -> cheapestTo(grid, cheapest, row, column - 1)
            column == 0 -> cheapestTo(grid, cheapest, row - 1, column)
            else -> minOf(
                cheapestTo(grid, cheapest, row - 1, column),
                cheapestTo(grid, cheapest, row, column - 1),
            )
        }
        cheapest[row][column] = arrival + grid[row][column]
        return cheapest[row][column]
    }
}
