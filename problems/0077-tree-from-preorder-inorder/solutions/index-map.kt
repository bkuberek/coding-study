import cs.support.*

class Solution {
    fun buildTree(preorder: IntArray, inorder: IntArray): TreeNode? {
        val position = HashMap<Int, Int>(inorder.size * 2)
        inorder.forEachIndexed { index, value -> position[value] = index }
        var nextRoot = 0

        /** Tree whose in-order walk is inorder[low, high); its root is the next pre-order value. */
        fun build(low: Int, high: Int): TreeNode? {
            if (low == high) return null
            val value = preorder[nextRoot++]
            val split = position.getValue(value)
            return TreeNode(value).apply {
                left = build(low, split)
                right = build(split + 1, high)
            }
        }

        return build(0, inorder.size)
    }
}
