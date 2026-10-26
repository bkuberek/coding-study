import cs.support.*

class Solution {
    fun serializeDeserialize(root: TreeNode?): TreeNode? = deserialize(serialize(root))

    fun serialize(root: TreeNode?): String {
        val tokens = ArrayList<String>()
        val queue = ArrayDeque<TreeNode?>()
        queue.addLast(root)
        while (queue.isNotEmpty()) {
            val node = queue.removeFirst()
            if (node == null) {
                tokens.add(MISSING)
                continue
            }
            tokens.add(node.`val`.toString())
            queue.addLast(node.left)
            queue.addLast(node.right)
        }
        return tokens.joinToString(SEPARATOR)
    }

    fun deserialize(data: String): TreeNode? {
        val tokens = data.split(SEPARATOR)
        if (tokens[0] == MISSING) return null
        val root = TreeNode(tokens[0].toInt())
        val queue = ArrayDeque<TreeNode>()
        queue.addLast(root)
        var position = 1
        // Every node was written with exactly two child tokens, in queue order.
        while (queue.isNotEmpty()) {
            val node = queue.removeFirst()
            val left = tokens[position++]
            val right = tokens[position++]
            if (left != MISSING) node.left = TreeNode(left.toInt()).also(queue::addLast)
            if (right != MISSING) node.right = TreeNode(right.toInt()).also(queue::addLast)
        }
        return root
    }

    private companion object {
        const val MISSING = "#"
        const val SEPARATOR = ","
    }
}
