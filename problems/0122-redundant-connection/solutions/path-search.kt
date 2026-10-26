class Solution {
    fun findRedundantConnection(edges: Array<IntArray>): IntArray {
        val neighbors = List(edges.size + 1) { mutableListOf<Int>() }

        fun connected(start: Int, goal: Int): Boolean {
            val seen = BooleanArray(neighbors.size)
            val stack = ArrayDeque(listOf(start))
            seen[start] = true
            while (stack.isNotEmpty()) {
                val node = stack.removeLast()
                if (node == goal) return true
                for (neighbor in neighbors[node]) {
                    if (!seen[neighbor]) {
                        seen[neighbor] = true
                        stack.addLast(neighbor)
                    }
                }
            }
            return false
        }

        for (edge in edges) {
            val (a, b) = edge
            // The first edge whose ends are already connected closes the only cycle.
            if (connected(a, b)) return edge
            neighbors[a].add(b)
            neighbors[b].add(a)
        }
        return IntArray(0)
    }
}
