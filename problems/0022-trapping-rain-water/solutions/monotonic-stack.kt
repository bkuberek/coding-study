class Solution {
    fun trap(height: IntArray): Int {
        var water = 0
        val falling = ArrayDeque<Int>()
        for (right in height.indices) {
            while (falling.isNotEmpty() && height[falling.last()] < height[right]) {
                val bottom = height[falling.removeLast()]
                if (falling.isEmpty()) break
                val left = falling.last()
                val level = minOf(height[left], height[right])
                water += (right - left - 1) * (level - bottom)
            }
            falling.addLast(right)
        }
        return water
    }
}
