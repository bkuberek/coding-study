import kotlin.math.abs

class Solution {
    fun findTargetSumWays(nums: IntArray, target: Int): Int {
        val total = nums.sum()
        // With P the plus part: P - (total - P) = target, so P = (total + target) / 2.
        if (abs(target) > total || (total + target) % 2 != 0) return 0
        val plus = (total + target) / 2
        // ways[p] counts the subsets of the values seen so far that add up to p.
        val ways = IntArray(plus + 1)
        ways[0] = 1
        for (value in nums) {
            // Decreasing p: ways[p - value] still excludes this value, so it is used at most once.
            for (p in plus downTo value) {
                ways[p] += ways[p - value]
            }
        }
        return ways[plus]
    }
}
