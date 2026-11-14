class Solution {
    fun subarraySum(nums: IntArray, k: Int): Int {
        var count = 0
        for (start in nums.indices) {
            var total = 0
            for (end in start until nums.size) {
                total += nums[end]
                if (total == k) count++
            }
        }
        return count
    }
}
