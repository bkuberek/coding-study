import cs.support.*

class Solution {
    /** The answer if both p and q are below [root], else whichever of them is below, else null. */
    fun lowestCommonAncestor(root: TreeNode?, p: TreeNode?, q: TreeNode?): TreeNode? {
        if (root == null || root === p || root === q) return root
        val left = lowestCommonAncestor(root.left, p, q)
        val right = lowestCommonAncestor(root.right, p, q)
        if (left != null && right != null) return root
        return left ?: right
    }
}
