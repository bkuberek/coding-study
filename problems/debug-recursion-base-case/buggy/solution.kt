// Debug: Recursion Base Case. Some tests fail: find the bug and fix it.
import cs.support.*

class Solution {
    fun hasPathSum(root: TreeNode?, target: Int): Boolean {
        if (root == null) return target == 0
        val remaining = target - root.`val`
        return hasPathSum(root.left, remaining) || hasPathSum(root.right, remaining)
    }
}
