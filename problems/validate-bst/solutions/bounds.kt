import cs.support.*

class Solution {
    // Long bounds lie outside the Int range, so they never collide with a real value.
    fun isValidBST(root: TreeNode?): Boolean = within(root, Long.MIN_VALUE, Long.MAX_VALUE)

    /** Is every value of the subtree strictly between [low] and [high]? */
    private fun within(node: TreeNode?, low: Long, high: Long): Boolean {
        if (node == null) return true
        val value = node.`val`.toLong()
        if (value <= low || value >= high) return false
        return within(node.left, low, value) && within(node.right, value, high)
    }
}
