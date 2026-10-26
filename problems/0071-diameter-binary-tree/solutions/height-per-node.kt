import cs.support.*

class Solution {
    fun diameterOfBinaryTree(root: TreeNode?): Int {
        if (root == null) return 0
        val turningHere = height(root.left) + height(root.right)
        return maxOf(turningHere, diameterOfBinaryTree(root.left), diameterOfBinaryTree(root.right))
    }

    /** Number of nodes on the longest downward path from [node]. */
    private fun height(node: TreeNode?): Int =
        if (node == null) 0 else 1 + maxOf(height(node.left), height(node.right))
}
