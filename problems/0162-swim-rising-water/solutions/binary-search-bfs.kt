class Solution {
    fun swimInWater(grid: Array<IntArray>): Int {
        val n = grid.size

        // Can the goal be reached when the water stands at `time`?
        fun reachable(time: Int): Boolean {
            if (grid[0][0] > time) return false
            val seen = Array(n) { BooleanArray(n) }
            seen[0][0] = true
            val queue = ArrayDeque<Int>()
            queue.addLast(0)
            while (queue.isNotEmpty()) {
                val cell = queue.removeFirst()
                val r = cell / n
                val c = cell % n
                if (r == n - 1 && c == n - 1) return true
                for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                    if (nr in 0 until n && nc in 0 until n && !seen[nr][nc] && grid[nr][nc] <= time) {
                        seen[nr][nc] = true
                        queue.addLast(nr * n + nc)
                    }
                }
            }
            return false
        }

        // The answer is at least both corner heights and at most the highest floor.
        var low = maxOf(grid[0][0], grid[n - 1][n - 1])
        var high = n * n - 1
        while (low < high) {
            val middle = (low + high) / 2
            if (reachable(middle)) high = middle else low = middle + 1
        }
        return low
    }
}
