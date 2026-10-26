import cs.support.*

class Solution {
    fun diameterOfBinaryTree(root: TreeNode?): Int {
        var best = 0

        fun height(node: TreeNode?): Int {
            if (node == null) return 0
            val left = height(node.left)
            val right = height(node.right)
            best = maxOf(best, left + right)
            return 1 + maxOf(left, right)
        }

        height(root)
        return best
    }
}
