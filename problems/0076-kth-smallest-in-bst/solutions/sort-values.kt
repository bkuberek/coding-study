import cs.support.*

class Solution {
    fun kthSmallest(root: TreeNode?, k: Int): Int {
        val values = ArrayList<Int>()
        val pending = ArrayDeque<TreeNode?>()
        pending.addLast(root)
        while (pending.isNotEmpty()) {
            val node = pending.removeLast() ?: continue
            values.add(node.`val`)
            pending.addLast(node.left)
            pending.addLast(node.right)
        }
        return values.sorted()[k - 1]
    }
}
