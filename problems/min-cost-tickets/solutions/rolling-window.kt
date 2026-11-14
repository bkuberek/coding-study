private const val WINDOW = 30

class Solution {
    fun mincostTickets(days: IntArray, costs: IntArray): Int {
        // cost[d % WINDOW] holds the cheapest cover of days 1..d for the last 30 calendar days;
        // nothing older is ever read, because the longest pass lasts 30 days.
        val cost = IntArray(WINDOW)
        var nextTrip = 0
        for (d in 1..days.last()) {
            val previous = cost[(d - 1) % WINDOW]
            if (d != days[nextTrip]) {
                cost[d % WINDOW] = previous
                continue
            }
            nextTrip++
            val weekAgo = if (d >= 7) cost[(d - 7) % WINDOW] else 0
            val monthAgo = if (d >= WINDOW) cost[d % WINDOW] else 0
            cost[d % WINDOW] = minOf(previous + costs[0], weekAgo + costs[1], monthAgo + costs[2])
        }
        return cost[days.last() % WINDOW]
    }
}
