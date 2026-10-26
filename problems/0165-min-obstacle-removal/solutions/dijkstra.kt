import java.util.PriorityQueue

class Solution {
    fun minimumObstacles(grid: Array<IntArray>): Int {
        val rows = grid.size
        val cols = grid[0].size
        val settled = Array(rows) { BooleanArray(cols) }
        // Entries are (removals so far, cell index); entering a cell costs its own value.
        val heap = PriorityQueue<Pair<Int, Int>>(compareBy { it.first })
        heap.add(0 to 0)
        while (true) {
            val (cost, cell) = heap.poll()
            val r = cell / cols
            val c = cell % cols
            if (settled[r][c]) continue // an outdated entry: settled earlier at a lower cost
            settled[r][c] = true
            if (r == rows - 1 && c == cols - 1) return cost
            for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                if (nr in 0 until rows && nc in 0 until cols && !settled[nr][nc]) {
                    heap.add(cost + grid[nr][nc] to nr * cols + nc)
                }
            }
        }
    }
}
