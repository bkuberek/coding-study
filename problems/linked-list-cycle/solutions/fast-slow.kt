import cs.support.*

class Solution {
    fun hasCycle(head: ListNode?): Boolean {
        var slow = head
        var fast = head
        // The fast pointer reaches the end first when there is no loop; inside a loop it gains
        // one node per step on the slow pointer and must land on it.
        while (fast?.next != null) {
            slow = slow?.next
            fast = fast.next.next
            if (slow === fast) return true
        }
        return false
    }
}
