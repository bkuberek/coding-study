import cs.support.*

class Solution {
    fun rightSideView(root: TreeNode?): List<Int> {
        val view = mutableListOf<Int>()
        var level = listOfNotNull(root)
        while (level.isNotEmpty()) {
            view.add(level.last().`val`)
            level = level.flatMap { listOfNotNull(it.left, it.right) }
        }
        return view
    }
}
