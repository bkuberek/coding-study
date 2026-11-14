class Solution {
    fun floodFill(grid: Array<IntArray>, row: Int, col: Int, newColor: Int): Array<IntArray> {
        val oldColor = grid[row][col]
        if (oldColor == newColor) return grid
        val queue = ArrayDeque<Pair<Int, Int>>()
        grid[row][col] = newColor
        queue.addLast(row to col)
        while (queue.isNotEmpty()) {
            val (r, c) = queue.removeFirst()
            for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                if (nr in grid.indices && nc in grid[0].indices && grid[nr][nc] == oldColor) {
                    grid[nr][nc] = newColor
                    queue.addLast(nr to nc)
                }
            }
        }
        return grid
    }
}
