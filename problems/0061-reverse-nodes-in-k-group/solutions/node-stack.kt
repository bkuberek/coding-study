import cs.support.*

class Solution {
    fun reverseKGroup(head: ListNode?, k: Int): ListNode? {
        val dummy = ListNode()
        var tail = dummy
        var node = head
        val stack = ArrayDeque<ListNode>()
        while (true) {
            // Take up to k nodes; popping them off the stack yields the group reversed.
            var probe = node
            while (probe != null && stack.size < k) {
                stack.addLast(probe)
                probe = probe.next
            }
            if (stack.size < k) {
                tail.next = node // a short tail keeps its order
                return dummy.next
            }
            while (stack.isNotEmpty()) {
                tail.next = stack.removeLast()
                tail = tail.next
            }
            node = probe
        }
    }
}
