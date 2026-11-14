import cs.support.*;

public class Solution {
    public boolean hasCycle(ListNode head) {
        ListNode slow = head;
        ListNode fast = head;
        // The fast pointer reaches the end first when there is no loop; inside a loop it gains
        // one node per step on the slow pointer and must land on it.
        while (fast != null && fast.next != null) {
            slow = slow.next;
            fast = fast.next.next;
            if (slow == fast) {
                return true;
            }
        }
        return false;
    }
}
