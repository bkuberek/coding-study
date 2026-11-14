class Solution {
    fun findRedundantConnection(edges: Array<IntArray>): IntArray {
        val parent = IntArray(edges.size + 1) { it } // parent[x] == x marks a root

        fun find(start: Int): Int {
            var x = start
            while (parent[x] != x) x = parent[x]
            return x
        }

        for (edge in edges) {
            val rootA = find(edge[0])
            val rootB = find(edge[1])
            if (rootA == rootB) return edge // the ends are already connected: this edge closes the cycle
            parent[rootA] = rootB // no balancing: trees can grow into long chains
        }
        return IntArray(0)
    }
}
