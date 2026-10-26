class Solution {
    fun maxArea(height: IntArray): Int {
        var left = 0
        var right = height.size - 1
        var best = 0
        while (left < right) {
            val width = right - left
            if (height[left] < height[right]) {
                best = maxOf(best, width * height[left])
                left++
            } else {
                best = maxOf(best, width * height[right])
                right--
            }
        }
        return best
    }
}
