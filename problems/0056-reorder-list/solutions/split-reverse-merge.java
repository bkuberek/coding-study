import cs.support.*;

public class Solution {
    public void reorderList(ListNode head) {
        if (head == null) {
            return;
        }
        // 1. Find the end of the front half: for n nodes, `slow` stops at node (n - 1) / 2.
        ListNode slow = head;
        ListNode fast = head;
        while (fast.next != null && fast.next.next != null) {
            slow = slow.next;
            fast = fast.next.next;
        }
        // 2. Cut the list and reverse the back half.
        ListNode back = reverse(slow.next);
        slow.next = null;
        // 3. Interleave; the front half is never shorter than the back half.
        ListNode front = head;
        while (back != null) {
            ListNode frontNext = front.next;
            ListNode backNext = back.next;
            front.next = back;
            back.next = frontNext;
            front = frontNext;
            back = backNext;
        }
    }

    private static ListNode reverse(ListNode head) {
        ListNode previous = null;
        while (head != null) {
            ListNode following = head.next;
            head.next = previous;
            previous = head;
            head = following;
        }
        return previous;
    }
}
