import cs.support.*;

public class Solution {
    public ListNode reverseKGroup(ListNode head, int k) {
        ListNode dummy = new ListNode(0, head);
        ListNode before = dummy; // the node just before the next group
        while (true) {
            ListNode last = before;
            for (int step = 0; step < k && last != null; step++) {
                last = last.next;
            }
            if (last == null) {
                return dummy.next; // fewer than k nodes remain: leave them as they are
            }
            ListNode after = last.next;
            // Reverse the group; its first node ends up last, pointing at `after`.
            ListNode first = before.next;
            ListNode previous = after;
            ListNode current = first;
            while (current != after) {
                ListNode following = current.next;
                current.next = previous;
                previous = current;
                current = following;
            }
            before.next = last;
            before = first;
        }
    }
}
