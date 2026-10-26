class Solution {
    fun lengthOfLIS(nums: IntArray): Int {
        // memo[start] is the longest increasing subsequence that begins at nums[start], or 0.
        val memo = IntArray(nums.size)

        fun longestFrom(start: Int): Int {
            if (memo[start] == 0) {
                var best = 1
                for (following in start + 1 until nums.size) {
                    if (nums[following] > nums[start]) {
                        best = maxOf(best, 1 + longestFrom(following))
                    }
                }
                memo[start] = best
            }
            return memo[start]
        }

        return nums.indices.maxOf { longestFrom(it) }
    }
}
