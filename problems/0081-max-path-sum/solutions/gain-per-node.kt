import cs.support.*

class Solution {
    fun maxPathSum(root: TreeNode?): Int {
        val node = requireNotNull(root) { "the tree is non-empty" }
        var best = node.`val` + maxOf(0, gain(node.left)) + maxOf(0, gain(node.right))
        node.left?.let { best = maxOf(best, maxPathSum(it)) }
        node.right?.let { best = maxOf(best, maxPathSum(it)) }
        return best
    }

    /** Largest sum of a path that starts at [node] and only goes down (0 for no node). */
    private fun gain(node: TreeNode?): Int =
        if (node == null) 0 else node.`val` + maxOf(0, gain(node.left), gain(node.right))
}
