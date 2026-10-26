import cs.support.*

class Solution {
    fun mergeTwoLists(list1: ListNode?, list2: ListNode?): ListNode? {
        // The dummy node gives the merged list a fixed place to start, so the first splice
        // needs no special case.
        val dummy = ListNode()
        var tail = dummy
        var first = list1
        var second = list2
        while (first != null && second != null) {
            if (first.`val` <= second.`val`) {
                tail.next = first
                first = first.next
            } else {
                tail.next = second
                second = second.next
            }
            tail = tail.next
        }
        // At most one list has nodes left, and they are already sorted: link them as a block.
        tail.next = first ?: second
        return dummy.next
    }
}
