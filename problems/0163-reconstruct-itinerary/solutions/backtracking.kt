private const val START = "JFK"

class Solution {
    fun findItinerary(tickets: Array<Array<String>>): List<String> {
        // Destinations per airport in increasing order, with a used flag per ticket.
        val destinations = tickets.groupBy({ it[0] }, { it[1] }).mapValues { (_, targets) -> targets.sorted() }
        val used = destinations.mapValues { (_, targets) -> BooleanArray(targets.size) }
        val route = mutableListOf(START)

        // Tries to complete the route from `airport`; on failure, leaves the route unchanged.
        fun extend(airport: String): Boolean {
            if (route.size == tickets.size + 1) return true
            val targets = destinations[airport] ?: return false
            val flags = used.getValue(airport)
            for (i in targets.indices) {
                if (flags[i]) continue
                // An identical ticket was just tried from this same position and failed.
                if (i > 0 && targets[i] == targets[i - 1] && !flags[i - 1]) continue
                flags[i] = true
                route.add(targets[i])
                if (extend(targets[i])) return true
                route.removeAt(route.lastIndex)
                flags[i] = false
            }
            return false
        }

        extend(START)
        return route
    }
}
