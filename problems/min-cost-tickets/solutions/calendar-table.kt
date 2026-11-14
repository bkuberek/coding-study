class Solution {
    fun mincostTickets(days: IntArray, costs: IntArray): Int {
        val lastDay = days.last()
        val travel = BooleanArray(lastDay + 1)
        for (day in days) travel[day] = true
        // cost[d] is the cheapest way to cover every trip on calendar days 1..d.
        val cost = IntArray(lastDay + 1)
        for (d in 1..lastDay) {
            cost[d] = if (!travel[d]) {
                cost[d - 1]
            } else {
                minOf(
                    cost[d - 1] + costs[0],
                    cost[maxOf(0, d - 7)] + costs[1],
                    cost[maxOf(0, d - 30)] + costs[2],
                )
            }
        }
        return cost[lastDay]
    }
}
