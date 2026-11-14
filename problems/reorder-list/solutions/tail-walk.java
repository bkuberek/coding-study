import cs.support.*;

public class Solution {
    public void reorderList(ListNode head) {
        ListNode current = head;
        // Each round moves the current tail right after `current`; two or fewer nodes from
        // `current` onward are already in their final order.
        while (current != null && current.next != null && current.next.next != null) {
            ListNode beforeTail = current;
            while (beforeTail.next.next != null) {
                beforeTail = beforeTail.next;
            }
            ListNode tail = beforeTail.next;
            beforeTail.next = null;
            tail.next = current.next;
            current.next = tail;
            current = tail.next;
        }
    }
}
