import cs.support.*

class Solution {
    fun copyList(head: ListNode?): ListNode? {
        val sentinel = ListNode()
        var tail = sentinel
        var node = head
        while (node != null) {
            tail.next = ListNode(node.`val`)
            tail = tail.next
            node = node.next
        }
        return sentinel.next
    }
}
