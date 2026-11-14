class Solution {
    fun pacificAtlantic(heights: Array<IntArray>): Array<IntArray> {
        val rows = heights.size
        val cols = heights[0].size

        // Cells whose water can reach a coast: search uphill from all its cells at once.
        fun climb(isCoast: (Int, Int) -> Boolean): BooleanArray {
            val reached = BooleanArray(rows * cols)
            val queue = ArrayDeque<Int>()
            for (r in 0 until rows) {
                for (c in 0 until cols) {
                    if (isCoast(r, c)) {
                        reached[r * cols + c] = true
                        queue.addLast(r * cols + c)
                    }
                }
            }
            while (queue.isNotEmpty()) {
                val cell = queue.removeFirst()
                val r = cell / cols
                val c = cell % cols
                for ((nr, nc) in listOf(r + 1 to c, r - 1 to c, r to c + 1, r to c - 1)) {
                    if (nr !in 0 until rows || nc !in 0 until cols) continue
                    val next = nr * cols + nc
                    if (!reached[next] && heights[nr][nc] >= heights[r][c]) {
                        reached[next] = true
                        queue.addLast(next)
                    }
                }
            }
            return reached
        }

        val pacific = climb { r, c -> r == 0 || c == 0 }
        val atlantic = climb { r, c -> r == rows - 1 || c == cols - 1 }
        return (0 until rows * cols)
            .filter { pacific[it] && atlantic[it] }
            .map { intArrayOf(it / cols, it % cols) }
            .toTypedArray()
    }
}
