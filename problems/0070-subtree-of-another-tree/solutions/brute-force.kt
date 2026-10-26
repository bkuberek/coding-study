import cs.support.*

class Solution {
    fun isSubtree(root: TreeNode?, subRoot: TreeNode?): Boolean {
        if (root == null) return false
        return same(root, subRoot) || isSubtree(root.left, subRoot) || isSubtree(root.right, subRoot)
    }

    private fun same(a: TreeNode?, b: TreeNode?): Boolean {
        if (a == null || b == null) return a === b
        return a.`val` == b.`val` && same(a.left, b.left) && same(a.right, b.right)
    }
}
