class Solution {
    fun criticalConnections(n: Int, connections: Array<IntArray>): List<List<Int>> {
        val adjacency = Array(n) { mutableListOf<Int>() }
        for ((a, b) in connections) {
            adjacency[a].add(b)
            adjacency[b].add(a)
        }
        // discovered[v] is the order in which v was first reached (-1: not yet).
        // low[v] is the earliest discovery time reachable from v's subtree using at most one
        // cable that is not a tree edge.
        val discovered = IntArray(n) { -1 }
        val low = IntArray(n)
        val bridges = mutableListOf<List<Int>>()
        var clock = 0

        fun visit(server: Int, parent: Int) {
            discovered[server] = clock
            low[server] = clock
            clock++
            for (neighbor in adjacency[server]) {
                if (neighbor == parent) continue // the tree edge we arrived by is not a way back
                if (discovered[neighbor] == -1) {
                    visit(neighbor, server)
                    low[server] = minOf(low[server], low[neighbor])
                    if (low[neighbor] > discovered[server]) bridges.add(listOf(server, neighbor))
                } else {
                    low[server] = minOf(low[server], discovered[neighbor])
                }
            }
        }

        visit(0, -1)
        return bridges
    }
}
