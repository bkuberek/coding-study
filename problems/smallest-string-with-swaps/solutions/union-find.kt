private class DisjointSets(count: Int) {
    private val parent = IntArray(count) { it }
    private val size = IntArray(count) { 1 } // size[r]: number of positions in the tree rooted at r

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

    fun union(a: Int, b: Int) {
        var rootA = find(a)
        var rootB = find(b)
        if (rootA == rootB) return
        if (size[rootA] < size[rootB]) rootA = rootB.also { rootB = rootA }
        parent[rootB] = rootA // union by size: the smaller tree goes under the larger
        size[rootA] += size[rootB]
    }
}

class Solution {
    fun smallestStringWithSwaps(s: String, pairs: Array<IntArray>): String {
        val sets = DisjointSets(s.length)
        for ((a, b) in pairs) sets.union(a, b)
        val letters = s.toCharArray()
        // groupBy keeps the positions of each group in increasing order.
        for (positions in s.indices.groupBy(sets::find).values) {
            positions.zip(positions.map { s[it] }.sorted()).forEach { (position, letter) -> letters[position] = letter }
        }
        return String(letters)
    }
}
