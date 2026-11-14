import cs.support.*

class Solution {
    fun verticalOrder(root: TreeNode?): List<List<Int>> {
        if (root == null) return emptyList()
        val columns = HashMap<Int, MutableList<Int>>()
        val queue = ArrayDeque<Pair<TreeNode, Int>>()
        queue.addLast(root to 0)
        var leftmost = 0
        var rightmost = 0
        while (queue.isNotEmpty()) {
            val (node, column) = queue.removeFirst()
            columns.getOrPut(column) { mutableListOf() }.add(node.`val`)
            leftmost = minOf(leftmost, column)
            rightmost = maxOf(rightmost, column)
            node.left?.let { queue.addLast(it to column - 1) }
            node.right?.let { queue.addLast(it to column + 1) }
        }
        // Columns form a contiguous range: every path from the root moves one column per step.
        return (leftmost..rightmost).map { columns.getValue(it) }
    }
}
