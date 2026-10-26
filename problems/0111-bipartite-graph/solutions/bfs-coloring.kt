private const val UNCOLORED = -1

class Solution {
    fun isBipartite(graph: Array<IntArray>): Boolean {
        val color = IntArray(graph.size) { UNCOLORED }
        val queue = ArrayDeque<Int>()
        // Every piece of the graph needs its own start node.
        for (start in graph.indices) {
            if (color[start] != UNCOLORED) continue
            color[start] = 0
            queue.addLast(start)
            while (queue.isNotEmpty()) {
                val node = queue.removeFirst()
                for (neighbor in graph[node]) {
                    when (color[neighbor]) {
                        UNCOLORED -> {
                            color[neighbor] = 1 - color[node]
                            queue.addLast(neighbor)
                        }
                        color[node] -> return false
                    }
                }
            }
        }
        return true
    }
}
