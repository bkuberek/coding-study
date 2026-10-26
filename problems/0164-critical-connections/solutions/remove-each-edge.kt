class Solution {
    fun criticalConnections(n: Int, connections: Array<IntArray>): List<List<Int>> {
        val adjacency = Array(n) { mutableListOf<Pair<Int, Int>>() }
        for ((index, cable) in connections.withIndex()) {
            val (a, b) = cable
            adjacency[a].add(b to index)
            adjacency[b].add(a to index)
        }

        // Can every server still be reached from server 0 when cable `skipped` is cut?
        fun connectedWithout(skipped: Int): Boolean {
            val seen = BooleanArray(n)
            seen[0] = true
            val stack = ArrayDeque(listOf(0))
            var reached = 1
            while (stack.isNotEmpty()) {
                for ((neighbor, index) in adjacency[stack.removeLast()]) {
                    if (index != skipped && !seen[neighbor]) {
                        seen[neighbor] = true
                        reached++
                        stack.addLast(neighbor)
                    }
                }
            }
            return reached == n
        }

        return connections.indices.filter { !connectedWithout(it) }.map { connections[it].toList() }
    }
}
