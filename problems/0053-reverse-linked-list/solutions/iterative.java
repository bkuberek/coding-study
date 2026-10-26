import cs.support.*;

public class Solution {
    public ListNode reverseList(ListNode head) {
        ListNode previous = null;
        ListNode current = head;
        while (current != null) {
            // Save the rest of the list before the link that leads to it is redirected.
            ListNode following = current.next;
            current.next = previous;
            previous = current;
            current = following;
        }
        return previous;
    }
}
