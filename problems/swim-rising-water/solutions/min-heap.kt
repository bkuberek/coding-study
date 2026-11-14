import java.util.PriorityQueue

class Solution {
    fun swimInWater(grid: Array<IntArray>): Int {
        val n = grid.size
        val seen = Array(n) { BooleanArray(n) }
        seen[0][0] = true
        // Entries are (highest floor on the route so far, cell index).
        val heap = PriorityQueue<Pair<Int, Int>>(compareBy { it.first })
        heap.add(grid[0][0] to 0)
        while (true) {
            val (level, cell) = heap.poll()
            val r = cell / n
            val c = cell % n
            if (r == n - 1 && c == n - 1) return level
            for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                if (nr in 0 until n && nc in 0 until n && !seen[nr][nc]) {
                    seen[nr][nc] = true
                    heap.add(maxOf(level, grid[nr][nc]) to nr * n + nc)
                }
            }
        }
    }
}
