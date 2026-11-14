private const val UNREACHED = Int.MAX_VALUE

class Solution {
    fun networkDelayTime(times: Array<IntArray>, n: Int, k: Int): Int {
        val arrival = IntArray(n + 1) { UNREACHED }
        arrival[k] = 0
        // After round i, every node whose fastest route uses at most i links has its final time;
        // a fastest route has at most n - 1 links, and a round without changes ends early.
        for (round in 1 until n) {
            var changed = false
            for ((u, v, w) in times) {
                if (arrival[u] != UNREACHED && arrival[u] + w < arrival[v]) {
                    arrival[v] = arrival[u] + w
                    changed = true
                }
            }
            if (!changed) break
        }
        val latest = (1..n).maxOf { arrival[it] }
        return if (latest == UNREACHED) -1 else latest
    }
}
