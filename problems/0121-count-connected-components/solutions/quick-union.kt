class Solution {
    fun countComponents(n: Int, edges: Array<IntArray>): Int {
        val parent = IntArray(n) { it } // parent[x] == x marks a root

        fun find(start: Int): Int {
            var x = start
            while (parent[x] != x) x = parent[x]
            return x
        }

        var components = n
        for ((a, b) in edges) {
            val rootA = find(a)
            val rootB = find(b)
            if (rootA != rootB) {
                parent[rootA] = rootB // no balancing: trees can grow into long chains
                components--
            }
        }
        return components
    }
}
