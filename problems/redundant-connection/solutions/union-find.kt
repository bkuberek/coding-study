private class DisjointSets(count: Int) {
    private val parent = IntArray(count) { it }
    private val size = IntArray(count) { 1 } // size[r]: number of nodes in the tree rooted at r

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
    fun findRedundantConnection(edges: Array<IntArray>): IntArray {
        val sets = DisjointSets(edges.size + 1)
        // The ends of the first edge that merges nothing were already connected.
        return edges.firstOrNull { (a, b) -> !sets.union(a, b) } ?: IntArray(0)
    }
}
