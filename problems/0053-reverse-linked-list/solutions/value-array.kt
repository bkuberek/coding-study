import cs.support.*

class Solution {
    fun reverseList(head: ListNode?): ListNode? {
        val values = ArrayList<Int>()
        var node = head
        while (node != null) {
            values.add(node.`val`)
            node = node.next
        }
        // Second pass: the same nodes, in the same order, receive the values from the back.
        node = head
        while (node != null) {
            node.`val` = values.removeAt(values.lastIndex)
            node = node.next
        }
        return head
    }
}
