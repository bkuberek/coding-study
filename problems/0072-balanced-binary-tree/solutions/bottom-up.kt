import cs.support.*
import kotlin.math.abs

class Solution {
    fun isBalanced(root: TreeNode?): Boolean = checkedHeight(root) != UNBALANCED

    /** Height of [node], or [UNBALANCED] as soon as any subtree below it is unbalanced. */
    private fun checkedHeight(node: TreeNode?): Int {
        if (node == null) return 0
        val left = checkedHeight(node.left)
        if (left == UNBALANCED) return UNBALANCED
        val right = checkedHeight(node.right)
        if (right == UNBALANCED || abs(left - right) > 1) return UNBALANCED
        return 1 + maxOf(left, right)
    }

    private companion object {
        const val UNBALANCED = -1
    }
}
