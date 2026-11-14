import cs.support.*

class Solution {
    fun reverseKGroup(head: ListNode?, k: Int): ListNode? {
        val nodes = generateSequence(head) { it.next }.toList()
        // Reverse every full chunk; a shorter chunk at the end keeps its order.
        val values = nodes.map { it.`val` }
            .chunked(k) { chunk -> if (chunk.size == k) chunk.reversed() else chunk.toList() }
            .flatten()
        nodes.forEachIndexed { index, node -> node.`val` = values[index] }
        return head
    }
}
