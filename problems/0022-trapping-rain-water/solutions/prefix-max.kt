class Solution {
    fun trap(height: IntArray): Int {
        val n = height.size
        val leftMax = IntArray(n)
        val rightMax = IntArray(n)
        leftMax[0] = height[0]
        for (i in 1 until n) {
            leftMax[i] = maxOf(leftMax[i - 1], height[i])
        }
        rightMax[n - 1] = height[n - 1]
        for (i in n - 2 downTo 0) {
            rightMax[i] = maxOf(rightMax[i + 1], height[i])
        }
        return height.indices.sumOf { i -> minOf(leftMax[i], rightMax[i]) - height[i] }
    }
}
