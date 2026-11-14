class Solution {
    fun rob(nums: IntArray): Int {
        // Before each house: withoutLast and withLast are the best totals for the prefixes
        // that end two houses back and one house back.
        var withoutLast = 0
        var withLast = 0
        for (cash in nums) {
            val current = maxOf(withLast, withoutLast + cash)
            withoutLast = withLast
            withLast = current
        }
        return withLast
    }
}
