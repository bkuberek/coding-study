import cs.support.*;

public class Solution {
    public ListNode reverseList(ListNode head) {
        if (head == null || head.next == null) {
            return head;
        }
        ListNode newHead = reverseList(head.next);
        // head.next is now the tail of the reversed rest; head goes after it.
        head.next.next = head;
        head.next = null;
        return newHead;
    }
}
