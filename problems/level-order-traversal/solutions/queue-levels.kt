import cs.support.*

class Solution {
    fun levelOrder(root: TreeNode?): List<List<Int>> {
        val levels = mutableListOf<List<Int>>()
        val queue = ArrayDeque<TreeNode>()
        root?.let(queue::addLast)
        while (queue.isNotEmpty()) {
            val level = List(queue.size) {
                val node = queue.removeFirst()
                node.left?.let(queue::addLast)
                node.right?.let(queue::addLast)
                node.`val`
            }
            levels.add(level)
        }
        return levels
    }
}
