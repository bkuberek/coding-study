private val DURATIONS = intArrayOf(1, 7, 30)

class Solution {
    fun mincostTickets(days: IntArray, costs: IntArray): Int {
        // A pass bought for days[index] covers through days[index] + duration - 1.
        fun firstUncovered(index: Int, duration: Int): Int {
            var following = index
            while (following < days.size && days[following] < days[index] + duration) following++
            return following
        }

        // memo[index] is the cheapest cover of days[index..], or -1 when unknown.
        val memo = IntArray(days.size) { -1 }

        fun cheapestFrom(index: Int): Int {
            if (index == days.size) return 0
            if (memo[index] == -1) {
                memo[index] = DURATIONS.indices.minOf { pass ->
                    costs[pass] + cheapestFrom(firstUncovered(index, DURATIONS[pass]))
                }
            }
            return memo[index]
        }

        return cheapestFrom(0)
    }
}
