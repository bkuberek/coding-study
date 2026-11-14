import cs.support.*

class Solution {
    fun hasCycle(head: ListNode?): Boolean {
        // ListNode does not override equals, so the set compares node identities.
        val visited = HashSet<ListNode>()
        var node = head
        while (node != null) {
            if (!visited.add(node)) return true
            node = node.next
        }
        return false
    }
}
