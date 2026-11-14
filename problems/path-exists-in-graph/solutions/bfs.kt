class Solution {
    fun hasPath(n: Int, edges: Array<IntArray>, source: Int, target: Int): Boolean {
        // neighbors[node] lists every node joined to `node`; each connection works both ways.
        val neighbors = Array(n) { mutableListOf<Int>() }
        for ((a, b) in edges) {
            neighbors[a].add(b)
            neighbors[b].add(a)
        }
        val seen = BooleanArray(n)
        seen[source] = true
        val queue = ArrayDeque<Int>()
        queue.addLast(source)
        while (queue.isNotEmpty()) {
            val node = queue.removeFirst()
            if (node == target) return true
            for (neighbor in neighbors[node]) {
                if (!seen[neighbor]) {
                    seen[neighbor] = true
                    queue.addLast(neighbor)
                }
            }
        }
        return false
    }
}
