class Solution {
    fun findMaximizedCapital(k: Int, w: Int, profits: IntArray, capital: IntArray): Int {
        val used = BooleanArray(profits.size)
        var funds = w
        repeat(k) {
            var best = -1
            for (index in profits.indices) {
                if (!used[index] && capital[index] <= funds && (best < 0 || profits[index] > profits[best])) {
                    best = index
                }
            }
            // Nothing affordable now, and capital cannot grow any more.
            if (best < 0) return funds
            used[best] = true
            funds += profits[best]
        }
        return funds
    }
}
