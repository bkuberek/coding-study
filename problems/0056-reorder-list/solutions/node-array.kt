import cs.support.*

class Solution {
    fun reorderList(head: ListNode?) {
        val nodes = generateSequence(head) { it.next }.toList()
        if (nodes.isEmpty()) return
        var left = 0
        var right = nodes.lastIndex
        // Alternate: front node -> back node -> next front node, until the indexes meet.
        while (left < right) {
            nodes[left].next = nodes[right]
            left++
            if (left == right) break
            nodes[right].next = nodes[left]
            right--
        }
        nodes[left].next = null
    }
}
