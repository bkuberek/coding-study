class Solution {
    fun rob(nums: IntArray): Int {
        // memo[house] is the most cash obtainable from houses house..end, or -1 when unknown.
        val memo = IntArray(nums.size) { -1 }

        fun bestFrom(house: Int): Int {
            if (house >= nums.size) return 0
            if (memo[house] == -1) {
                memo[house] = maxOf(bestFrom(house + 1), nums[house] + bestFrom(house + 2))
            }
            return memo[house]
        }

        return bestFrom(0)
    }
}
