import cs.support.*

class Solution {
    fun mergeTwoLists(list1: ListNode?, list2: ListNode?): ListNode? {
        val values = ArrayList<Int>()
        for (start in listOf(list1, list2)) {
            var node = start
            while (node != null) {
                values.add(node.`val`)
                node = node.next
            }
        }
        values.sort()
        val dummy = ListNode()
        var tail = dummy
        for (value in values) {
            tail.next = ListNode(value)
            tail = tail.next
        }
        return dummy.next
    }
}
