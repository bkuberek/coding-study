import java.util.PriorityQueue

class Solution {
    fun findTheCity(n: Int, edges: Array<IntArray>, distanceThreshold: Int): Int {
        val graph = Array(n) { mutableListOf<Pair<Int, Int>>() }
        for ((a, b, w) in edges) {
            graph[a].add(b to w)
            graph[b].add(a to w)
        }

        // Counts the other cities within the threshold, never pushing a distance beyond it.
        fun reachable(source: Int): Int {
            val settled = BooleanArray(n)
            // Entries are (distance, city).
            val heap = PriorityQueue<Pair<Int, Int>>(compareBy { it.first })
            heap.add(0 to source)
            var count = -1
            while (heap.isNotEmpty()) {
                val (distance, city) = heap.poll()
                if (settled[city]) continue
                settled[city] = true
                count++
                for ((neighbor, w) in graph[city]) {
                    if (!settled[neighbor] && distance + w <= distanceThreshold) heap.add(distance + w to neighbor)
                }
            }
            return count
        }

        var bestCity = -1
        var bestCount = n + 1
        for (city in 0 until n) {
            val count = reachable(city)
            // `<=` lets a later city win a tie.
            if (count <= bestCount) {
                bestCity = city
                bestCount = count
            }
        }
        return bestCity
    }
}
