import cs.support.*

class Solution {
    fun isSameTree(p: TreeNode?, q: TreeNode?): Boolean {
        val pending = ArrayDeque<Pair<TreeNode?, TreeNode?>>()
        pending.addLast(p to q)
        while (pending.isNotEmpty()) {
            val (a, b) = pending.removeLast()
            if (a == null && b == null) continue
            if (a == null || b == null || a.`val` != b.`val`) return false
            pending.addLast(a.right to b.right)
            pending.addLast(a.left to b.left)
        }
        return true
    }
}
