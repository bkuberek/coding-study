import cs.support.*
import java.util.PriorityQueue

class Solution {
    fun mergeKLists(lists: Array<ListNode?>): ListNode? {
        // PriorityQueue is a min-heap; the comparator orders nodes by value.
        val heap = PriorityQueue<ListNode>(compareBy { it.`val` })
        lists.filterNotNullTo(heap)
        val dummy = ListNode()
        var tail = dummy
        while (heap.isNotEmpty()) {
            val node = heap.poll()
            tail.next = node
            tail = node
            node.next?.let(heap::offer)
        }
        return dummy.next
    }
}
