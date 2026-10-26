class Solution {
    fun numIslands(grid: Array<CharArray>): Int {
        val rows = grid.size
        val cols = grid[0].size
        val visited = Array(rows) { BooleanArray(cols) }
        var islands = 0
        val queue = ArrayDeque<Int>()
        for (row in 0 until rows) {
            for (col in 0 until cols) {
                if (grid[row][col] != '1' || visited[row][col]) continue
                islands++
                visited[row][col] = true
                queue.addLast(row * cols + col)
                while (queue.isNotEmpty()) {
                    val cell = queue.removeFirst()
                    val r = cell / cols
                    val c = cell % cols
                    for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                        if (nr in 0 until rows && nc in 0 until cols && grid[nr][nc] == '1' && !visited[nr][nc]) {
                            visited[nr][nc] = true
                            queue.addLast(nr * cols + nc)
                        }
                    }
                }
            }
        }
        return islands
    }
}
