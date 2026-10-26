import cs.support.*

class Solution {
    private data class Entry(val column: Int, val row: Int, val value: Int)

    fun verticalOrder(root: TreeNode?): List<List<Int>> {
        val entries = mutableListOf<Entry>()

        fun visit(node: TreeNode?, column: Int, row: Int) {
            if (node == null) return
            entries.add(Entry(column, row, node.`val`))
            visit(node.left, column - 1, row + 1)
            visit(node.right, column + 1, row + 1)
        }

        visit(root, 0, 0)
        // sortedWith is stable, so pre-order (left to right) survives among ties.
        return entries
            .sortedWith(compareBy<Entry>({ it.column }, { it.row }))
            .groupBy { it.column }
            .values
            .map { group -> group.map { it.value } }
    }
}
