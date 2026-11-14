import cs.support.*

class Solution {
    fun removeNthFromEnd(head: ListNode?, n: Int): ListNode? {
        var length = 0
        var node = head
        while (node != null) {
            length++
            node = node.next
        }
        // The dummy node is the predecessor of the head, so removing the head is not special.
        val dummy = ListNode(0, head)
        var before: ListNode = dummy
        repeat(length - n) { before = before.next }
        before.next = before.next.next
        return dummy.next
    }
}
