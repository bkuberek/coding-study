class Solution {
    fun checkSubarraySum(nums: IntArray, k: Int): Boolean {
        for (start in nums.indices) {
            // Sums reach 10^14, so the running total must be a Long.
            var total = nums[start].toLong()
            for (end in start + 1 until nums.size) {
                total += nums[end]
                if (total % k == 0L) return true
            }
        }
        return false
    }
}
