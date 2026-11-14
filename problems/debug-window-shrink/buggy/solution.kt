// Debug: Window Shrink. Some tests fail: find the bug and fix it.
class Solution {
    fun maxDistinctWindowSum(nums: IntArray, k: Int): Int {
        val counts = HashMap<Int, Int>()
        var windowSum = 0
        var best = 0
        for (right in nums.indices) {
            counts[nums[right]] = (counts[nums[right]] ?: 0) + 1
            windowSum += nums[right]
            if (right >= k) {
                val outgoing = nums[right - k]
                counts[outgoing] = counts.getValue(outgoing) - 1
                windowSum -= outgoing
            }
            if (right >= k - 1 && counts.size == k) {
                best = maxOf(best, windowSum)
            }
        }
        return best
    }
}
