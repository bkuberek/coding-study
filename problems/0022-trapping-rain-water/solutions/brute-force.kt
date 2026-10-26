class Solution {
    fun trap(height: IntArray): Int {
        var water = 0
        for (i in height.indices) {
            var leftMax = 0
            for (j in 0..i) {
                leftMax = maxOf(leftMax, height[j])
            }
            var rightMax = 0
            for (j in i until height.size) {
                rightMax = maxOf(rightMax, height[j])
            }
            water += minOf(leftMax, rightMax) - height[i]
        }
        return water
    }
}
