class Solution {
    fun rob(nums: IntArray): Int {
        // best[i] is the most cash obtainable from the first i houses.
        val best = IntArray(nums.size + 1)
        best[1] = nums[0]
        for (i in 2..nums.size) {
            best[i] = maxOf(best[i - 1], best[i - 2] + nums[i - 1])
        }
        return best[nums.size]
    }
}
