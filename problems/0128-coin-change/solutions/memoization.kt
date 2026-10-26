class Solution {
    fun coinChange(coins: IntArray, amount: Int): Int {
        // fewest(x) never exceeds `unreachable`, which stands for "x cannot be paid".
        val unreachable = amount + 1
        val unknown = -1
        val memo = IntArray(amount + 1) { unknown }

        fun fewest(remaining: Int): Int {
            if (remaining == 0) return 0
            if (memo[remaining] == unknown) {
                var best = unreachable
                for (coin in coins) {
                    if (coin <= remaining) {
                        best = minOf(best, fewest(remaining - coin) + 1)
                    }
                }
                memo[remaining] = best
            }
            return memo[remaining]
        }

        val answer = fewest(amount)
        return if (answer == unreachable) -1 else answer
    }
}
