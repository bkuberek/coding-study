class Solution {
    fun largestRectangleArea(heights: IntArray): Int {
        var best = 0
        for (left in heights.indices) {
            // The tallest rectangle spanning bars left..right is as high as the lowest of them.
            var lowest = heights[left]
            for (right in left until heights.size) {
                lowest = minOf(lowest, heights[right])
                best = maxOf(best, lowest * (right - left + 1))
            }
        }
        return best
    }
}
