class Solution {
    fun missingNumber(nums: IntArray): Int {
        // Start with n, then fold in every index and value; present numbers cancel in pairs.
        var result = nums.size
        for ((index, value) in nums.withIndex()) {
            result = result xor index xor value
        }
        return result
    }
}
