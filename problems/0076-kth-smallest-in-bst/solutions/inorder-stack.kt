import cs.support.*

class Solution {
    fun kthSmallest(root: TreeNode?, k: Int): Int {
        val stack = ArrayDeque<TreeNode>()
        var node = root
        var remaining = k
        while (true) {
            while (node != null) {
                stack.addLast(node)
                node = node.left
            }
            val current = stack.removeLast()
            if (--remaining == 0) return current.`val`
            node = current.right
        }
    }
}
