class Solution {
    fun minSubArrayLen(target: Int, nums: IntArray): Int {
        var best = 0
        var total = 0
        var left = 0
        for (right in nums.indices) {
            total += nums[right]
            while (total >= target) {
                if (best == 0 || right - left + 1 < best) best = right - left + 1
                total -= nums[left++]
            }
        }
        return best
    }
}
