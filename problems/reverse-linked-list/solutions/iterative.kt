import cs.support.*

class Solution {
    fun reverseList(head: ListNode?): ListNode? {
        var previous: ListNode? = null
        var current = head
        while (current != null) {
            // Save the rest of the list before the link that leads to it is redirected.
            val following = current.next
            current.next = previous
            previous = current
            current = following
        }
        return previous
    }
}
