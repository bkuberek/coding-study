class Solution {
    fun maxSubArray(nums: IntArray): Int {
        var best = nums[0]
        for (start in nums.indices) {
            var total = 0
            for (end in start until nums.size) {
                total += nums[end]
                best = maxOf(best, total)
            }
        }
        return best
    }
}
