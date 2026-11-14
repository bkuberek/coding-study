import cs.support.*

class Solution {
    fun mergeKLists(lists: Array<ListNode?>): ListNode? =
        lists.fold(null as ListNode?) { merged, head -> merge(merged, head) }

    private fun merge(left: ListNode?, right: ListNode?): ListNode? {
        val dummy = ListNode()
        var tail = dummy
        var first = left
        var second = right
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
        tail.next = first ?: second
        return dummy.next
    }
}
