import java.util.PriorityQueue

private const val START = "JFK"

class Solution {
    fun findItinerary(tickets: Array<Array<String>>): List<String> {
        // A min-heap of destinations per airport: poll() always takes the smallest unused one.
        val destinations = HashMap<String, PriorityQueue<String>>()
        for ((origin, target) in tickets) destinations.getOrPut(origin) { PriorityQueue() }.add(target)
        val route = ArrayDeque<String>()
        val stack = ArrayDeque(listOf(START))
        while (stack.isNotEmpty()) {
            val targets = destinations[stack.last()]
            if (targets != null && targets.isNotEmpty()) {
                stack.addLast(targets.poll())
            } else {
                // Stuck: this airport comes last among what is left, so it joins the route now.
                route.addFirst(stack.removeLast())
            }
        }
        return route.toList()
    }
}
