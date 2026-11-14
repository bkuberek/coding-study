import cs.support.*

class Solution {
    fun isSubtree(root: TreeNode?, subRoot: TreeNode?): Boolean = occurs(tokens(subRoot), tokens(root))

    /** Pre-order values with [NO_NODE] for every missing child: a unique description of the tree. */
    private fun tokens(root: TreeNode?): IntArray {
        val out = ArrayList<Int>()
        val pending = ArrayDeque<TreeNode?>()
        pending.addLast(root)
        while (pending.isNotEmpty()) {
            val node = pending.removeLast()
            if (node == null) {
                out.add(NO_NODE)
                continue
            }
            out.add(node.`val`)
            pending.addLast(node.right)
            pending.addLast(node.left)
        }
        return out.toIntArray()
    }

    /** Knuth-Morris-Pratt: does [pattern] occur as a contiguous block of [text]? */
    private fun occurs(pattern: IntArray, text: IntArray): Boolean {
        val border = IntArray(pattern.size)
        var length = 0
        for (i in 1 until pattern.size) {
            while (length > 0 && pattern[i] != pattern[length]) length = border[length - 1]
            if (pattern[i] == pattern[length]) length++
            border[i] = length
        }
        var matched = 0
        for (token in text) {
            while (matched > 0 && token != pattern[matched]) matched = border[matched - 1]
            if (token == pattern[matched]) {
                matched++
                if (matched == pattern.size) return true
            }
        }
        return false
    }

    private companion object {
        // Values lie in [-10^4, 10^4], so this marker for a missing child never equals a value.
        const val NO_NODE = Int.MIN_VALUE
    }
}
