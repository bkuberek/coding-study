class RangeModule {
    /** EMPTY or COVERED with no children, or MIXED with both children. */
    private class Node(var state: Int) {
        var left: Node? = null
        var right: Node? = null
    }

    private val root = Node(EMPTY)

    fun addRange(left: Int, right: Int) = assign(root, LOW, HIGH, left, right, COVERED)

    fun queryRange(left: Int, right: Int): Boolean = covered(root, LOW, HIGH, left, right)

    fun removeRange(left: Int, right: Int) = assign(root, LOW, HIGH, left, right, EMPTY)

    private fun assign(node: Node, low: Int, high: Int, left: Int, right: Int, value: Int) {
        if (right <= low || high <= left) return
        if (left <= low && high <= right) {
            node.state = value
            node.left = null
            node.right = null
            return
        }
        // A uniform node is split: both halves inherit its state.
        val first = node.left ?: Node(node.state).also { node.left = it }
        val second = node.right ?: Node(node.state).also { node.right = it }
        val middle = low + (high - low) / 2
        assign(first, low, middle, left, right, value)
        assign(second, middle, high, left, right, value)
        if (first.state == second.state && first.state != MIXED) {
            node.state = first.state // both halves agree: collapse
            node.left = null
            node.right = null
        } else {
            node.state = MIXED
        }
    }

    private fun covered(node: Node, low: Int, high: Int, left: Int, right: Int): Boolean {
        if (right <= low || high <= left) return true
        val first = node.left ?: return node.state == COVERED
        val second = node.right ?: return node.state == COVERED
        val middle = low + (high - low) / 2
        return covered(first, low, middle, left, right) && covered(second, middle, high, left, right)
    }

    private companion object {
        const val EMPTY = 0
        const val COVERED = 1
        const val MIXED = 2
        const val LOW = 1
        const val HIGH = 1_000_000_000 // every range lies inside [1, 10^9)
    }
}
