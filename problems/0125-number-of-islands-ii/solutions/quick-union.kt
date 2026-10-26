private val STEPS = arrayOf(intArrayOf(1, 0), intArrayOf(-1, 0), intArrayOf(0, 1), intArrayOf(0, -1))

class Solution {
    fun numIslands2(m: Int, n: Int, positions: Array<IntArray>): IntArray {
        val parent = IntArray(m * n) { it } // cell r * n + c; parent[x] == x marks a root
        val land = BooleanArray(m * n)

        fun find(start: Int): Int {
            var x = start
            while (parent[x] != x) x = parent[x]
            return x
        }

        var islands = 0
        return IntArray(positions.size) { i ->
            val (r, c) = positions[i]
            val cell = r * n + c
            if (!land[cell]) {
                land[cell] = true
                islands++ // a new island, until it merges with its neighbors
                for ((dr, dc) in STEPS) {
                    val nr = r + dr
                    val nc = c + dc
                    if (nr in 0 until m && nc in 0 until n && land[nr * n + nc]) {
                        val rootNeighbor = find(nr * n + nc)
                        val rootCell = find(cell)
                        if (rootNeighbor != rootCell) {
                            parent[rootNeighbor] = rootCell // no balancing: chains can grow
                            islands--
                        }
                    }
                }
            }
            islands
        }
    }
}
