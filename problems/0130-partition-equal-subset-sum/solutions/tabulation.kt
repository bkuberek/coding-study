class Solution {
    fun canPartition(nums: IntArray): Boolean {
        val total = nums.sum()
        if (total % 2 == 1) return false
        val target = total / 2
        // reach[i][s] is true when some of the first i elements add up to exactly s.
        val reach = Array(nums.size + 1) { BooleanArray(target + 1) }
        reach[0][0] = true
        for (i in 1..nums.size) {
            val value = nums[i - 1]
            for (s in 0..target) {
                reach[i][s] = reach[i - 1][s] || (s >= value && reach[i - 1][s - value])
            }
        }
        return reach[nums.size][target]
    }
}
