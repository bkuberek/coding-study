private fun largestInHistogram(heights: IntArray): Int {
    var best = 0
    // Indexes of bars whose heights strictly increase from bottom to top.
    val rising = ArrayDeque<Int>()
    // One extra bar of height 0 at the end pops every bar still waiting.
    for (index in 0..heights.size) {
        val height = if (index < heights.size) heights[index] else 0
        while (rising.isNotEmpty() && heights[rising.last()] >= height) {
            val top = rising.removeLast()
            val left = rising.lastOrNull() ?: -1
            best = maxOf(best, heights[top] * (index - left - 1))
        }
        rising.addLast(index)
    }
    return best
}

class Solution {
    fun maximalRectangle(matrix: Array<CharArray>): Int {
        // heights[c] counts the consecutive ones in column c ending at the current row.
        val heights = IntArray(matrix[0].size)
        var best = 0
        for (row in matrix) {
            for (c in row.indices) {
                heights[c] = if (row[c] == '1') heights[c] + 1 else 0
            }
            best = maxOf(best, largestInHistogram(heights))
        }
        return best
    }
}
