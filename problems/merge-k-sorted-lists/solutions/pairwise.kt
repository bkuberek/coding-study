import cs.support.*

class Solution {
    fun mergeKLists(lists: Array<ListNode?>): ListNode? {
        if (lists.isEmpty()) return null
        // Each round merges neighbours (0 with 1, 2 with 3, ...), halving the number of lists;
        // every node takes part in one merge per round, and there are ceil(log2 k) rounds.
        var heads: List<ListNode?> = lists.asList()
        while (heads.size > 1) {
            heads = heads.chunked(2) { pair -> merge(pair[0], pair.getOrNull(1)) }
        }
        return heads[0]
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
