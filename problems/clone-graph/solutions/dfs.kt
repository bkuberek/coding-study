import cs.support.*

class Solution {
    fun cloneGraph(node: GraphNode?): GraphNode? {
        val clones = HashMap<GraphNode, GraphNode>()

        fun copy(original: GraphNode): GraphNode {
            clones[original]?.let { return it }
            // Register the copy before recursing, so a cycle back to this node finds it.
            val clone = GraphNode(original.`val`)
            clones[original] = clone
            for (neighbor in original.neighbors) {
                clone.neighbors.add(copy(neighbor))
            }
            return clone
        }

        return node?.let { copy(it) }
    }
}
