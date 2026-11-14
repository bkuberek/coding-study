import cs.support.*

class Solution {
    fun reorderList(head: ListNode?) {
        if (head == null) return
        // 1. Find the end of the front half: for n nodes, `slow` stops at node (n - 1) / 2.
        var slow: ListNode = head
        var fast: ListNode = head
        while (fast.next?.next != null) {
            slow = slow.next
            fast = fast.next.next
        }
        // 2. Cut the list and reverse the back half.
        var back = reverse(slow.next)
        slow.next = null
        // 3. Interleave; the front half is never shorter than the back half, so `front` only
        // runs out together with `back` (even length) or one node after it (odd length).
        var front: ListNode? = head
        while (front != null && back != null) {
            val frontNext: ListNode? = front.next
            val backNext: ListNode? = back.next
            front.next = back
            back.next = frontNext
            front = frontNext
            back = backNext
        }
    }

    private fun reverse(head: ListNode?): ListNode? {
        var previous: ListNode? = null
        var current = head
        while (current != null) {
            val following = current.next
            current.next = previous
            previous = current
            current = following
        }
        return previous
    }
}
