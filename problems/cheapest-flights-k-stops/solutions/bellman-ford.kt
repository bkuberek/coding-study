private const val UNREACHED = Int.MAX_VALUE

class Solution {
    fun findCheapestPrice(n: Int, flights: Array<IntArray>, src: Int, dst: Int, k: Int): Int {
        // price[c] is the cheapest known price to reach c with at most `round` flights.
        var price = IntArray(n) { UNREACHED }
        price[src] = 0
        for (round in 0..k) {
            // Read from the previous round only, so one round never chains two flights.
            val previous = price
            price = previous.copyOf()
            var changed = false
            for ((start, end, cost) in flights) {
                if (previous[start] != UNREACHED && previous[start] + cost < price[end]) {
                    price[end] = previous[start] + cost
                    changed = true
                }
            }
            if (!changed) break
        }
        return if (price[dst] == UNREACHED) -1 else price[dst]
    }
}
