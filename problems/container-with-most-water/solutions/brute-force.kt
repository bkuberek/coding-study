class Solution {
    fun maxArea(height: IntArray): Int {
        var best = 0
        for (left in 0 until height.size - 1) {
            for (right in left + 1 until height.size) {
                best = maxOf(best, (right - left) * minOf(height[left], height[right]))
            }
        }
        return best
    }
}
