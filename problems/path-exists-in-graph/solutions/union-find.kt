private class DisjointSet(count: Int) {
    private val parent = IntArray(count) { it }
    private val size = IntArray(count) { 1 }

    fun find(start: Int): Int {
        var node = start
        // Path halving: point every other node on the way up at its grandparent.
        while (parent[node] != node) {
            parent[node] = parent[parent[node]]
            node = parent[node]
        }
        return node
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
    fun hasPath(n: Int, edges: Array<IntArray>, source: Int, target: Int): Boolean {
        val sets = DisjointSet(n)
        for ((a, b) in edges) sets.union(a, b)
        return sets.find(source) == sets.find(target)
    }
}
