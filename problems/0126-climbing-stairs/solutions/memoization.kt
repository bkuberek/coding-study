class Solution {
    fun climbStairs(n: Int): Int {
        // memo[step] is 0 until the count for `step` has been computed.
        val memo = IntArray(n + 1)

        fun ways(step: Int): Int {
            if (step <= 1) return 1
            if (memo[step] == 0) {
                memo[step] = ways(step - 1) + ways(step - 2)
            }
            return memo[step]
        }

        return ways(n)
    }
}
