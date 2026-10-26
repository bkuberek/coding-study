class Solution {
    fun largestRectangleArea(heights: IntArray): Int {
        var best = 0
        // Indexes of bars whose heights strictly increase from bottom to top.
        val rising = ArrayDeque<Int>()
        // One extra bar of height 0 at the end pops every bar still waiting.
        for (index in 0..heights.size) {
            val height = if (index < heights.size) heights[index] else 0
            while (rising.isNotEmpty() && heights[rising.last()] >= height) {
                val top = rising.removeLast()
                // The bar below `top` on the stack is lower, and so is `index` (or it is equal and
                // a later pop covers the full width): the rectangle spans the bars between them.
                val left = rising.lastOrNull() ?: -1
                best = maxOf(best, heights[top] * (index - left - 1))
            }
            rising.addLast(index)
        }
        return best
    }
}
