private val STEPS = (-1..1).flatMap { dr -> (-1..1).map { dc -> dr to dc } }.filter { it != 0 to 0 }

class Solution {
    fun shortestPathBinaryMatrix(grid: Array<IntArray>): Int {
        val n = grid.size
        if (grid[0][0] == 1 || grid[n - 1][n - 1] == 1) return -1
        // dist 0 means "not reached yet": every reached cell has a length of at least 1.
        val dist = Array(n) { IntArray(n) }
        dist[0][0] = 1
        val queue = ArrayDeque<Int>()
        queue.addLast(0)
        while (queue.isNotEmpty()) {
            val cell = queue.removeFirst()
            val r = cell / n
            val c = cell % n
            if (r == n - 1 && c == n - 1) return dist[r][c]
            for ((dr, dc) in STEPS) {
                val nr = r + dr
                val nc = c + dc
                if (nr in 0 until n && nc in 0 until n && grid[nr][nc] == 0 && dist[nr][nc] == 0) {
                    dist[nr][nc] = dist[r][c] + 1
                    queue.addLast(nr * n + nc)
                }
            }
        }
        return -1
    }
}
