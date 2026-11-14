import cs.support.*

class Solution {
    fun addTwoNumbers(l1: ListNode?, l2: ListNode?): ListNode? {
        val dummy = ListNode()
        var tail = dummy
        var first = l1
        var second = l2
        var carry = 0
        // Keep going while either number has digits left or a carry is still pending.
        while (first != null || second != null || carry > 0) {
            val total = carry + (first?.`val` ?: 0) + (second?.`val` ?: 0)
            first = first?.next
            second = second?.next
            carry = total / 10
            tail.next = ListNode(total % 10)
            tail = tail.next
        }
        return dummy.next
    }
}
