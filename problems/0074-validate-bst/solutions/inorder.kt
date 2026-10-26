import cs.support.*

class Solution {
    fun isValidBST(root: TreeNode?): Boolean {
        val stack = ArrayDeque<TreeNode>()
        var node = root
        // Below every Int, so the first value always passes.
        var previous = Long.MIN_VALUE
        while (stack.isNotEmpty() || node != null) {
            while (node != null) {
                stack.addLast(node)
                node = node.left
            }
            val current = stack.removeLast()
            if (current.`val` <= previous) return false
            previous = current.`val`.toLong()
            node = current.right
        }
        return true
    }
}
