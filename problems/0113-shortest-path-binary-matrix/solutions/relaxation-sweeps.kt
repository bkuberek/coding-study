private val STEPS = (-1..1).flatMap { dr -> (-1..1).map { dc -> dr to dc } }.filter { it != 0 to 0 }

class Solution {
    fun shortestPathBinaryMatrix(grid: Array<IntArray>): Int {
        val n = grid.size
        if (grid[0][0] == 1 || grid[n - 1][n - 1] == 1) return -1
        val unreached = n * n + 1
        val dist = Array(n) { IntArray(n) { unreached } }
        dist[0][0] = 1
        var forward = true
        var changed = true
        while (changed) {
            changed = false
            // Each sweep lets every open cell take the best distance offered by a neighbor;
            // alternating the scan direction lets improvements travel both ways quickly.
            for (i in 0 until n * n) {
                val cell = if (forward) i else n * n - 1 - i
                val r = cell / n
                val c = cell % n
                if (grid[r][c] == 1) continue
                for ((dr, dc) in STEPS) {
                    val nr = r + dr
                    val nc = c + dc
                    if (nr in 0 until n && nc in 0 until n && dist[nr][nc] + 1 < dist[r][c]) {
                        dist[r][c] = dist[nr][nc] + 1
                        changed = true
                    }
                }
            }
            forward = !forward
        }
        return if (dist[n - 1][n - 1] < unreached) dist[n - 1][n - 1] else -1
    }
}
