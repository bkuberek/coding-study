import cs.support.*

class Solution {
    fun isValidBST(root: TreeNode?): Boolean {
        if (root == null) return true
        root.left?.let { if (largest(it) >= root.`val`) return false }
        root.right?.let { if (smallest(it) <= root.`val`) return false }
        return isValidBST(root.left) && isValidBST(root.right)
    }

    /** Largest value anywhere in the subtree; it need not be a search tree, so scan it all. */
    private fun largest(node: TreeNode): Int =
        maxOf(node.`val`, node.left?.let(::largest) ?: Int.MIN_VALUE, node.right?.let(::largest) ?: Int.MIN_VALUE)

    private fun smallest(node: TreeNode): Int =
        minOf(node.`val`, node.left?.let(::smallest) ?: Int.MAX_VALUE, node.right?.let(::smallest) ?: Int.MAX_VALUE)
}
