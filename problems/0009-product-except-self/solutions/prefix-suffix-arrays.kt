class Solution {
    fun productExceptSelf(nums: IntArray): IntArray {
        val n = nums.size
        val left = IntArray(n) { 1 } // left[i] is the product of nums[0..i-1]
        for (i in 1 until n) {
            left[i] = left[i - 1] * nums[i - 1]
        }
        val right = IntArray(n) { 1 } // right[i] is the product of nums[i+1..n-1]
        for (i in n - 2 downTo 0) {
            right[i] = right[i + 1] * nums[i + 1]
        }
        return IntArray(n) { left[it] * right[it] }
    }
}
