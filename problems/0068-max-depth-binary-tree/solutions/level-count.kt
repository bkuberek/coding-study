import cs.support.*

class Solution {
    fun maxDepth(root: TreeNode?): Int {
        var level = listOfNotNull(root)
        var depth = 0
        while (level.isNotEmpty()) {
            depth++
            level = level.flatMap { listOfNotNull(it.left, it.right) }
        }
        return depth
    }
}
