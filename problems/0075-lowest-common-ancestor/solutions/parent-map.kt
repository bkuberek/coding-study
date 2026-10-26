import cs.support.*

class Solution {
    fun lowestCommonAncestor(root: TreeNode?, p: TreeNode?, q: TreeNode?): TreeNode? {
        if (root == null || p == null || q == null) return null
        // TreeNode keeps identity equals and hashCode, so nodes work as map keys.
        val parent = hashMapOf<TreeNode, TreeNode?>(root to null)
        val pending = ArrayDeque<TreeNode>().apply { addLast(root) }
        while (p !in parent || q !in parent) {
            val node = pending.removeLast()
            for (child in listOfNotNull(node.left, node.right)) {
                parent[child] = node
                pending.addLast(child)
            }
        }
        val ancestorsOfP = generateSequence(p) { parent[it] }.toHashSet()
        return generateSequence(q) { parent[it] }.first { it in ancestorsOfP }
    }
}
