import cs.support.*

class Solution {
    fun cloneGraph(node: GraphNode?): GraphNode? {
        if (node == null) return null
        val clones = hashMapOf(node to GraphNode(node.`val`))
        val queue = ArrayDeque(listOf(node))
        while (queue.isNotEmpty()) {
            val original = queue.removeFirst()
            val clone = clones.getValue(original)
            for (neighbor in original.neighbors) {
                val neighborClone = clones.getOrPut(neighbor) {
                    queue.addLast(neighbor)
                    GraphNode(neighbor.`val`)
                }
                clone.neighbors.add(neighborClone)
            }
        }
        return clones.getValue(node)
    }
}
