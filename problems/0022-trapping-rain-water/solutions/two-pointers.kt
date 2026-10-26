class Solution {
    fun trap(height: IntArray): Int {
        var left = 0
        var right = height.size - 1
        var leftMax = 0
        var rightMax = 0
        var water = 0
        while (left < right) {
            if (height[left] < height[right]) {
                leftMax = maxOf(leftMax, height[left])
                water += leftMax - height[left]
                left++
            } else {
                rightMax = maxOf(rightMax, height[right])
                water += rightMax - height[right]
                right--
            }
        }
        return water
    }
}
