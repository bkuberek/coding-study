import java.util.PriorityQueue

class Solution {
    fun networkDelayTime(times: Array<IntArray>, n: Int, k: Int): Int {
        val graph = Array(n + 1) { mutableListOf<Pair<Int, Int>>() }
        for ((u, v, w) in times) graph[u].add(v to w)
        val arrival = IntArray(n + 1) { -1 }
        // Entries are (time, node); PriorityQueue is a min-heap under this comparator.
        val heap = PriorityQueue<Pair<Int, Int>>(compareBy { it.first })
        heap.add(0 to k)
        var settled = 0
        var latest = 0
        while (heap.isNotEmpty()) {
            val (time, node) = heap.poll()
            if (arrival[node] != -1) continue // an outdated entry: settled earlier with a smaller time
            arrival[node] = time
            settled++
            latest = time
            for ((neighbor, w) in graph[node]) {
                if (arrival[neighbor] == -1) heap.add(time + w to neighbor)
            }
        }
        return if (settled == n) latest else -1
    }
}
