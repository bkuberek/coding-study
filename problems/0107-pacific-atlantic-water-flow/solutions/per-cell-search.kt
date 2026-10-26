class Solution {
    fun pacificAtlantic(heights: Array<IntArray>): Array<IntArray> {
        val rows = heights.size
        val cols = heights[0].size
        // seen[cell] == start marks cells visited by the search from start; no clearing needed.
        val seen = IntArray(rows * cols) { -1 }

        fun drainsToBoth(start: Int): Boolean {
            var pacific = false
            var atlantic = false
            val stack = ArrayDeque<Int>()
            seen[start] = start
            stack.addLast(start)
            while (stack.isNotEmpty()) {
                val cell = stack.removeLast()
                val r = cell / cols
                val c = cell % cols
                pacific = pacific || r == 0 || c == 0
                atlantic = atlantic || r == rows - 1 || c == cols - 1
                if (pacific && atlantic) return true
                for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                    if (nr !in 0 until rows || nc !in 0 until cols) continue
                    val next = nr * cols + nc
                    if (seen[next] != start && heights[nr][nc] <= heights[r][c]) {
                        seen[next] = start
                        stack.addLast(next)
                    }
                }
            }
            return false
        }

        val cells = mutableListOf<IntArray>()
        for (r in 0 until rows) {
            for (c in 0 until cols) {
                if (drainsToBoth(r * cols + c)) cells.add(intArrayOf(r, c))
            }
        }
        return cells.toTypedArray()
    }
}
