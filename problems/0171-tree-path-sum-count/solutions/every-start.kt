import cs.support.*

class Solution {
    fun pathSum(root: TreeNode?, targetSum: Int): Int {
        var count = 0
        val starts = ArrayDeque<TreeNode>()
        root?.let(starts::addLast)
        while (starts.isNotEmpty()) {
            val start = starts.removeLast()
            // Walk every downward path from start, carrying the sum so far.
            val pending = ArrayDeque<Pair<TreeNode, Int>>()
            pending.addLast(start to start.`val`)
            while (pending.isNotEmpty()) {
                val (node, total) = pending.removeLast()
                if (total == targetSum) count++
                node.left?.let { pending.addLast(it to total + it.`val`) }
                node.right?.let { pending.addLast(it to total + it.`val`) }
            }
            start.left?.let(starts::addLast)
            start.right?.let(starts::addLast)
        }
        return count
    }
}
