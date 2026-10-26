class Solution {
    fun minSubArrayLen(target: Int, nums: IntArray): Int {
        var best = 0
        for (start in nums.indices) {
            var total = 0
            for (end in start until nums.size) {
                total += nums[end]
                if (total >= target) {
                    if (best == 0 || end - start + 1 < best) best = end - start + 1
                    break
                }
            }
        }
        return best
    }
}
