class Solution {
    fun productExceptSelf(nums: IntArray): IntArray {
        val n = nums.size
        val answer = IntArray(n) { 1 }
        for (i in 1 until n) {
            answer[i] = answer[i - 1] * nums[i - 1] // product of nums[0..i-1]
        }
        var after = 1 // product of nums[i+1..n-1]
        for (i in n - 1 downTo 0) {
            answer[i] *= after
            after *= nums[i]
        }
        return answer
    }
}
