import cs.support.*

class Solution {
    fun sortList(head: ListNode?): ListNode? {
        val nodes = generateSequence(head) { it.next }.toList()
        val sorted = IntArray(nodes.size) { nodes[it].`val` }.apply { sort() }
        // Write the sorted values back into the same nodes, in list order.
        nodes.forEachIndexed { index, node -> node.`val` = sorted[index] }
        return head
    }
}
