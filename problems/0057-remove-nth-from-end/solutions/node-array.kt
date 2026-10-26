import cs.support.*

class Solution {
    fun removeNthFromEnd(head: ListNode?, n: Int): ListNode? {
        val nodes = generateSequence(head) { it.next }.toList()
        val target = nodes.size - n
        if (target == 0) return nodes[0].next
        nodes[target - 1].next = nodes[target].next
        return head
    }
}
