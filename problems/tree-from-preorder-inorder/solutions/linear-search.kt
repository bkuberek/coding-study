import cs.support.*

class Solution {
    fun buildTree(preorder: IntArray, inorder: IntArray): TreeNode? {
        /** Tree of the [size] values starting at preorder[preStart] and inorder[inStart]. */
        fun build(preStart: Int, inStart: Int, size: Int): TreeNode? {
            if (size == 0) return null
            val value = preorder[preStart]
            var split = inStart
            while (inorder[split] != value) split++
            val leftSize = split - inStart
            return TreeNode(value).apply {
                left = build(preStart + 1, inStart, leftSize)
                right = build(preStart + 1 + leftSize, split + 1, size - leftSize - 1)
            }
        }
        return build(0, 0, preorder.size)
    }
}
