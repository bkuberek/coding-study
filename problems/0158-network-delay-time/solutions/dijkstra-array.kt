private const val UNREACHED = Int.MAX_VALUE

class Solution {
    fun networkDelayTime(times: Array<IntArray>, n: Int, k: Int): Int {
        val graph = Array(n + 1) { mutableListOf<Pair<Int, Int>>() }
        for ((u, v, w) in times) graph[u].add(v to w)
        val arrival = IntArray(n + 1) { UNREACHED }
        arrival[k] = 0
        val settled = BooleanArray(n + 1)
        var latest = 0
        repeat(n) {
            // Scan for the unsettled node with the earliest arrival: O(n) per round, no heap.
            val node = (1..n).filter { !settled[it] }.minBy { arrival[it] }
            if (arrival[node] == UNREACHED) return -1
            settled[node] = true
            latest = arrival[node]
            for ((neighbor, w) in graph[node]) {
                arrival[neighbor] = minOf(arrival[neighbor], arrival[node] + w)
            }
        }
        return latest
    }
}
