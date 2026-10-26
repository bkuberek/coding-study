import cs.support.*;

public class Solution {
    public ListNode removeNthFromEnd(ListNode head, int n) {
        int length = 0;
        for (ListNode node = head; node != null; node = node.next) {
            length++;
        }
        // The dummy node is the predecessor of the head, so removing the head is not special.
        ListNode dummy = new ListNode(0, head);
        ListNode before = dummy;
        for (int step = 0; step < length - n; step++) {
            before = before.next;
        }
        before.next = before.next.next;
        return dummy.next;
    }
}
