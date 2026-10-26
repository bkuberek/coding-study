import cs.support.*

class Solution {
    fun invertTree(root: TreeNode?): TreeNode? {
        if (root == null) return null
        val invertedLeft = invertTree(root.left)
        root.left = invertTree(root.right)
        root.right = invertedLeft
        return root
    }
}
