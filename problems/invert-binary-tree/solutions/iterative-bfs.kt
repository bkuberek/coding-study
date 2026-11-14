import cs.support.*

class Solution {
    fun invertTree(root: TreeNode?): TreeNode? {
        val pending = ArrayDeque<TreeNode>()
        root?.let(pending::addLast)
        while (pending.isNotEmpty()) {
            val node = pending.removeFirst()
            node.left = node.right.also { node.right = node.left }
            node.left?.let(pending::addLast)
            node.right?.let(pending::addLast)
        }
        return root
    }
}
