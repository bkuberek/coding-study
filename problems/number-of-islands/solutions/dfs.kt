class Solution {
    fun numIslands(grid: Array<CharArray>): Int {
        val rows = grid.size
        val cols = grid[0].size
        var islands = 0
        val stack = ArrayDeque<Int>()
        for (row in 0 until rows) {
            for (col in 0 until cols) {
                if (grid[row][col] != '1') continue
                islands++
                // Sink each land square when it is discovered, so it is pushed at most once.
                grid[row][col] = '0'
                stack.addLast(row * cols + col)
                while (stack.isNotEmpty()) {
                    val cell = stack.removeLast()
                    val r = cell / cols
                    val c = cell % cols
                    for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                        if (nr in 0 until rows && nc in 0 until cols && grid[nr][nc] == '1') {
                            grid[nr][nc] = '0'
                            stack.addLast(nr * cols + nc)
                        }
                    }
                }
            }
        }
        return islands
    }
}
