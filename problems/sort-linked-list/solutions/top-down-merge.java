import cs.support.*;

public class Solution {
    public ListNode sortList(ListNode head) {
        if (head == null || head.next == null) {
            return head;
        }
        // Starting `fast` one node ahead makes `slow` stop at the end of the left half,
        // so a two-node list splits into one node and one node.
        ListNode slow = head;
        ListNode fast = head.next;
        while (fast != null && fast.next != null) {
            slow = slow.next;
            fast = fast.next.next;
        }
        ListNode right = slow.next;
        slow.next = null;
        return merge(sortList(head), sortList(right));
    }

    private static ListNode merge(ListNode left, ListNode right) {
        ListNode dummy = new ListNode();
        ListNode tail = dummy;
        while (left != null && right != null) {
            if (left.val <= right.val) {
                tail.next = left;
                left = left.next;
            } else {
                tail.next = right;
                right = right.next;
            }
            tail = tail.next;
        }
        tail.next = left != null ? left : right;
        return dummy.next;
    }
}
