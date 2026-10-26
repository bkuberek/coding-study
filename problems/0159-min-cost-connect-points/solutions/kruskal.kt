import kotlin.math.abs

// A pair is packed into one long: cost shl 20 or i shl 10 or j, so sorting longs sorts by cost.
private const val INDEX_BITS = 10
private const val INDEX_MASK = (1L shl INDEX_BITS) - 1

class Solution {
    fun minCostConnectPoints(points: Array<IntArray>): Int {
        val n = points.size
        val pairs = LongArray(n * (n - 1) / 2)
        var next = 0
        for (i in 0 until n) {
            for (j in i + 1 until n) {
                val cost = abs(points[i][0] - points[j][0]) + abs(points[i][1] - points[j][1])
                pairs[next++] = (cost.toLong() shl (2 * INDEX_BITS)) or (i.toLong() shl INDEX_BITS) or j.toLong()
            }
        }
        pairs.sort()

        val parent = IntArray(n) { it }
        fun find(start: Int): Int {
            var root = start
            while (parent[root] != root) root = parent[root]
            var node = start
            while (parent[node] != root) {
                val up = parent[node]
                parent[node] = root
                node = up
            }
            return root
        }

        var total = 0
        var cables = 0
        // Take pairs from cheapest to most expensive, keeping each one that joins two groups.
        for (packed in pairs) {
            if (cables == n - 1) break
            val rootI = find(((packed shr INDEX_BITS) and INDEX_MASK).toInt())
            val rootJ = find((packed and INDEX_MASK).toInt())
            if (rootI != rootJ) {
                parent[rootI] = rootJ
                total += (packed shr (2 * INDEX_BITS)).toInt()
                cables++
            }
        }
        return total
    }
}
