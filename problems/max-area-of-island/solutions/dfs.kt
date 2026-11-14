class Solution {
    fun maxAreaOfIsland(grid: Array<IntArray>): Int {
        val rows = grid.size
        val cols = grid[0].size
        val seen = Array(rows) { BooleanArray(cols) }
        val stack = ArrayDeque<Int>()
        var best = 0
        for (row in 0 until rows) {
            for (col in 0 until cols) {
                if (grid[row][col] != 1 || seen[row][col]) continue
                seen[row][col] = true
                stack.addLast(row * cols + col)
                var area = 0
                while (stack.isNotEmpty()) {
                    val cell = stack.removeLast()
                    area++
                    val r = cell / cols
                    val c = cell % cols
                    for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                        if (nr in 0 until rows && nc in 0 until cols && grid[nr][nc] == 1 && !seen[nr][nc]) {
                            seen[nr][nc] = true
                            stack.addLast(nr * cols + nc)
                        }
                    }
                }
                best = maxOf(best, area)
            }
        }
        return best
    }
}
