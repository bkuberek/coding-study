import cs.support.*

class Solution {
    fun reverseKGroup(head: ListNode?, k: Int): ListNode? {
        val dummy = ListNode(0, head)
        var before: ListNode = dummy // the node just before the next group
        while (true) {
            var last: ListNode? = before
            var step = 0
            while (step < k && last != null) {
                last = last.next
                step++
            }
            // Fewer than k nodes remain: leave them as they are.
            if (last == null) return dummy.next
            val after: ListNode? = last.next
            // Reverse the group; its first node ends up last, pointing at `after`.
            val first: ListNode = before.next
            var previous: ListNode? = after
            var current: ListNode? = first
            // `after` is null for a group that ends the list, so test `current` for null too.
            while (current != null && current !== after) {
                val following: ListNode? = current.next
                current.next = previous
                previous = current
                current = following
            }
            before.next = last
            before = first
        }
    }
}
