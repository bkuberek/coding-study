import cs.support.*

class BSTIterator(root: TreeNode?) {
    // Nodes whose left subtree is finished (or about to be) and that are not returned yet.
    private val stack = ArrayDeque<TreeNode>()

    init {
        pushLeftSpine(root)
    }

    private fun pushLeftSpine(node: TreeNode?) {
        var current = node
        while (current != null) {
            stack.addLast(current)
            current = current.left
        }
    }

    fun next(): Int {
        val node = stack.removeLast()
        pushLeftSpine(node.right)
        return node.`val`
    }

    fun hasNext(): Boolean = stack.isNotEmpty()
}
