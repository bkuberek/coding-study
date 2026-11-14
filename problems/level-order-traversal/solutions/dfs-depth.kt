import cs.support.*

class Solution {
    fun levelOrder(root: TreeNode?): List<List<Int>> {
        val levels = mutableListOf<MutableList<Int>>()

        fun visit(node: TreeNode?, depth: Int) {
            if (node == null) return
            if (depth == levels.size) levels.add(mutableListOf())
            levels[depth].add(node.`val`)
            visit(node.left, depth + 1)
            visit(node.right, depth + 1)
        }

        visit(root, 0)
        return levels
    }
}
