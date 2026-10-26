import cs.support.*;

public class Solution {
    public ListNode sortList(ListNode head) {
        ListNode dummy = new ListNode(); // head of the sorted prefix
        ListNode node = head;
        while (node != null) {
            ListNode following = node.next;
            // Find the last sorted node whose value is smaller, and insert after it.
            ListNode spot = dummy;
            while (spot.next != null && spot.next.val < node.val) {
                spot = spot.next;
            }
            node.next = spot.next;
            spot.next = node;
            node = following;
        }
        return dummy.next;
    }
}
