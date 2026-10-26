import cs.support.*

class Solution {
    fun reverseList(head: ListNode?): ListNode? {
        if (head?.next == null) return head
        val second: ListNode = head.next
        val newHead = reverseList(second)
        // second is now the tail of the reversed rest; head goes after it.
        second.next = head
        head.next = null
        return newHead
    }
}
