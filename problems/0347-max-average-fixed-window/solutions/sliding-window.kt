class Solution {
    fun maxWindowAverage(nums: IntArray, k: Int): Double {
        // A window sum is at most 10^5 * 10^4 = 10^9, which fits in an Int.
        var windowSum = 0
        for (i in 0 until k) windowSum += nums[i]
        var best = windowSum
        for (right in k until nums.size) {
            // Slide one step: the number at `right` enters and the one k places back leaves.
            windowSum += nums[right] - nums[right - k]
            best = maxOf(best, windowSum)
        }
        // Every window has k numbers, so the largest sum is the largest average. Divide once.
        return best.toDouble() / k
    }
}
