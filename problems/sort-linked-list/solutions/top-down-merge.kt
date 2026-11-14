import cs.support.*

class Solution {
    fun sortList(head: ListNode?): ListNode? {
        if (head?.next == null) return head
        // Starting `fast` one node ahead makes `slow` stop at the end of the left half,
        // so a two-node list splits into one node and one node.
        var slow: ListNode = head
        var fast: ListNode? = head.next
        while (fast?.next != null) {
            slow = slow.next
            fast = fast.next.next
        }
        val right: ListNode? = slow.next
        slow.next = null
        return merge(sortList(head), sortList(right))
    }

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
