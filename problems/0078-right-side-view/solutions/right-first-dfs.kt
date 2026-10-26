import cs.support.*

class Solution {
    fun rightSideView(root: TreeNode?): List<Int> {
        val view = mutableListOf<Int>()

        fun visit(node: TreeNode?, depth: Int) {
            if (node == null) return
            if (depth == view.size) view.add(node.`val`)
            visit(node.right, depth + 1)
            visit(node.left, depth + 1)
        }

        visit(root, 0)
        return view
    }
}
