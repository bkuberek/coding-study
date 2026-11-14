private val STEPS = arrayOf(intArrayOf(1, 0), intArrayOf(-1, 0), intArrayOf(0, 1), intArrayOf(0, -1))

private class DisjointSets(count: Int) {
    private val parent = IntArray(count) { it }
    private val size = IntArray(count) { 1 } // size[r]: number of cells in the tree rooted at r

    fun find(start: Int): Int {
        var root = start
        while (parent[root] != root) root = parent[root]
        var x = start
        while (parent[x] != root) { // path compression: point the whole path at the root
            val next = parent[x]
            parent[x] = root
            x = next
        }
        return root
    }

    /** Merges the sets of [a] and [b]; false when they were already one set. */
    fun union(a: Int, b: Int): Boolean {
        var rootA = find(a)
        var rootB = find(b)
        if (rootA == rootB) return false
        if (size[rootA] < size[rootB]) rootA = rootB.also { rootB = rootA }
        parent[rootB] = rootA // union by size: the smaller tree goes under the larger
        size[rootA] += size[rootB]
        return true
    }
}

class Solution {
    fun numIslands2(m: Int, n: Int, positions: Array<IntArray>): IntArray {
        val sets = DisjointSets(m * n) // cell r * n + c
        val land = BooleanArray(m * n)
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
                    if (nr in 0 until m && nc in 0 until n && land[nr * n + nc] && sets.union(nr * n + nc, cell)) {
                        islands--
                    }
                }
            }
            islands
        }
    }
}
