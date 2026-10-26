private class DisjointSet(count: Int) {
    private val parent = IntArray(count) { it }
    private val size = IntArray(count) { 1 }

    fun find(start: Int): Int {
        var root = start
        while (parent[root] != root) root = parent[root]
        var node = start
        while (parent[node] != root) {
            val next = parent[node]
            parent[node] = root
            node = next
        }
        return root
    }

    fun union(a: Int, b: Int) {
        var rootA = find(a)
        var rootB = find(b)
        if (rootA == rootB) return
        if (size[rootA] < size[rootB]) rootA = rootB.also { rootB = rootA }
        parent[rootB] = rootA
        size[rootA] += size[rootB]
    }
}

class Solution {
    fun isBipartite(graph: Array<IntArray>): Boolean {
        val teams = DisjointSet(graph.size)
        // All neighbors of a node must share a team, so they go into one group.
        for (neighbors in graph) {
            for (neighbor in neighbors) teams.union(neighbors[0], neighbor)
        }
        // A split exists exactly when no edge has both ends in one group.
        return graph.withIndex().all { (node, neighbors) ->
            neighbors.all { neighbor -> teams.find(node) != teams.find(neighbor) }
        }
    }
}
