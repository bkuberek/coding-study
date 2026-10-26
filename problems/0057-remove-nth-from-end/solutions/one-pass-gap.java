import cs.support.*;

public class Solution {
    public ListNode removeNthFromEnd(ListNode head, int n) {
        ListNode dummy = new ListNode(0, head);
        // `lead` starts n + 1 nodes ahead of `trail`; when `lead` falls off the end,
        // `trail` sits just before the node to remove.
        ListNode lead = dummy;
        for (int step = 0; step <= n; step++) {
            lead = lead.next;
        }
        ListNode trail = dummy;
        while (lead != null) {
            lead = lead.next;
            trail = trail.next;
        }
        trail.next = trail.next.next;
        return dummy.next;
    }
}
