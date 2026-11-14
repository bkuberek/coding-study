import kotlin.math.abs

class Solution {
    fun findTargetSumWays(nums: IntArray, target: Int): Int {
        val total = nums.sum()
        if (abs(target) > total) return 0
        // ways[i][running + total] counts the sign assignments of nums[:i] with that running total.
        val ways = Array(nums.size + 1) { IntArray(2 * total + 1) }
        ways[0][total] = 1
        for ((i, value) in nums.withIndex()) {
            for ((offset, count) in ways[i].withIndex()) {
                if (count > 0) {
                    ways[i + 1][offset + value] += count
                    ways[i + 1][offset - value] += count
                }
            }
        }
        return ways[nums.size][target + total]
    }
}
