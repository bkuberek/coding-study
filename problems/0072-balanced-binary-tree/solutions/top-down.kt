import cs.support.*
import kotlin.math.abs

class Solution {
    fun isBalanced(root: TreeNode?): Boolean {
        if (root == null) return true
        return abs(height(root.left) - height(root.right)) <= 1 && isBalanced(root.left) && isBalanced(root.right)
    }

    private fun height(node: TreeNode?): Int =
        if (node == null) 0 else 1 + maxOf(height(node.left), height(node.right))
}
