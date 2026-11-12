class Solution {
    fun maxWindowAverage(nums: IntArray, k: Int): Double {
        var best = Double.NEGATIVE_INFINITY
        for (start in 0..nums.size - k) {
            var sum = 0
            for (i in start until start + k) sum += nums[i]
            best = maxOf(best, sum.toDouble() / k)
        }
        return best
    }
}
