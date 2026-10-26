import cs.support.*

class Solution {
    fun maxPathSum(root: TreeNode?): Int {
        var best = requireNotNull(root) { "the tree is non-empty" }.`val`

        /** Best downward path sum from [node], recording the best path turning at it. */
        fun gain(node: TreeNode?): Int {
            if (node == null) return 0
            val left = maxOf(0, gain(node.left))
            val right = maxOf(0, gain(node.right))
            best = maxOf(best, node.`val` + left + right)
            return node.`val` + maxOf(left, right)
        }

        gain(root)
        return best
    }
}
