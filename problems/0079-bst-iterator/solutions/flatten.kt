import cs.support.*

class BSTIterator(root: TreeNode?) {
    private val values = ArrayList<Int>()
    private var position = 0

    init {
        collect(root)
    }

    private fun collect(node: TreeNode?) {
        if (node == null) return
        collect(node.left)
        values.add(node.`val`)
        collect(node.right)
    }

    fun next(): Int = values[position++]

    fun hasNext(): Boolean = position < values.size
}
