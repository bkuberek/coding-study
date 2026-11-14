import java.util.PriorityQueue

class Solution {
    fun findCheapestPrice(n: Int, flights: Array<IntArray>, src: Int, dst: Int, k: Int): Int {
        val graph = Array(n) { mutableListOf<Pair<Int, Int>>() }
        for ((start, end, cost) in flights) graph[start].add(end to cost)
        // fewest[c] is the fewest flights with which c was settled so far. States leave the heap
        // in order of price, so a later state for c is useful only if it used fewer flights.
        val fewest = IntArray(n) { k + 2 }
        // States are (price, city, used).
        val heap = PriorityQueue<Triple<Int, Int, Int>>(compareBy { it.first })
        heap.add(Triple(0, src, 0))
        while (heap.isNotEmpty()) {
            val (price, city, used) = heap.poll()
            if (city == dst) return price
            if (used >= fewest[city]) continue
            fewest[city] = used
            if (used == k + 1) continue // no flights left
            for ((neighbor, cost) in graph[city]) heap.add(Triple(price + cost, neighbor, used + 1))
        }
        return -1
    }
}
