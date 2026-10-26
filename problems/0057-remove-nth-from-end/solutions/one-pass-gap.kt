import cs.support.*

class Solution {
    fun removeNthFromEnd(head: ListNode?, n: Int): ListNode? {
        val dummy = ListNode(0, head)
        // `lead` starts n + 1 nodes ahead of `trail`; when `lead` falls off the end,
        // `trail` sits just before the node to remove.
        var lead: ListNode? = dummy
        for (step in 0..n) {
            lead = lead?.next
        }
        var trail: ListNode = dummy
        while (lead != null) {
            lead = lead.next
            trail = trail.next
        }
        trail.next = trail.next.next
        return dummy.next
    }
}
