import cs.support.*

class Solution {
    fun reorderList(head: ListNode?) {
        var current = head
        // Each round moves the current tail right after `current`; two or fewer nodes from
        // `current` onward are already in their final order.
        while (current?.next?.next != null) {
            var beforeTail: ListNode = current
            while (beforeTail.next.next != null) {
                beforeTail = beforeTail.next
            }
            val tail: ListNode = beforeTail.next
            beforeTail.next = null
            tail.next = current.next
            current.next = tail
            current = tail.next
        }
    }
}
