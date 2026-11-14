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
                val remaining = counts.getValue(outgoing) - 1
                if (remaining == 0) {
                    counts.remove(outgoing)
                } else {
                    counts[outgoing] = remaining
                }
                windowSum -= outgoing
            }
            if (right >= k - 1 && counts.size == k) {
                best = maxOf(best, windowSum)
            }
        }
        return best
    }
}
