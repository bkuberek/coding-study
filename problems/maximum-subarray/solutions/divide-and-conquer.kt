class Solution {
    fun maxSubArray(nums: IntArray): Int {
        // The best subarray sum within nums[low..high] (inclusive).
        fun bestIn(low: Int, high: Int): Int {
            if (low == high) return nums[low]
            val middle = (low + high) ushr 1
            // The best crossing subarray is a best suffix of the left half plus a best prefix
            // of the right half.
            var leftSuffix = nums[middle]
            var total = 0
            for (i in middle downTo low) {
                total += nums[i]
                leftSuffix = maxOf(leftSuffix, total)
            }
            var rightPrefix = nums[middle + 1]
            total = 0
            for (i in middle + 1..high) {
                total += nums[i]
                rightPrefix = maxOf(rightPrefix, total)
            }
            return maxOf(bestIn(low, middle), bestIn(middle + 1, high), leftSuffix + rightPrefix)
        }

        return bestIn(0, nums.size - 1)
    }
}
