import cs.support.*

class Solution {
    fun sortList(head: ListNode?): ListNode? {
        val dummy = ListNode() // head of the sorted prefix
        var node = head
        while (node != null) {
            val following: ListNode? = node.next
            // Find the last sorted node whose value is smaller, and insert after it.
            var spot: ListNode = dummy
            while (spot.next != null && spot.next.`val` < node.`val`) {
                spot = spot.next
            }
            node.next = spot.next
            spot.next = node
            node = following
        }
        return dummy.next
    }
}
