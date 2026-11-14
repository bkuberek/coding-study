import cs.support.*

class Solution {
    fun hasPathSum(root: TreeNode?, target: Int): Boolean {
        if (root == null) return false
        val remaining = target - root.`val`
        if (root.left == null && root.right == null) return remaining == 0
        return hasPathSum(root.left, remaining) || hasPathSum(root.right, remaining)
    }
}
