import cs.support.*

class Solution {
    fun pathSum(root: TreeNode?, targetSum: Int): Int {
        // onPath maps a prefix sum of the current root path to how many prefixes have it.
        val onPath = HashMap<Int, Int>()
        onPath[0] = 1

        fun countBelow(node: TreeNode?, sumAbove: Int): Int {
            if (node == null) return 0
            val total = sumAbove + node.`val`
            var found = onPath[total - targetSum] ?: 0
            onPath[total] = (onPath[total] ?: 0) + 1
            found += countBelow(node.left, total) + countBelow(node.right, total)
            onPath[total] = onPath.getValue(total) - 1 // leave the subtree
            return found
        }

        return countBelow(root, 0)
    }
}
