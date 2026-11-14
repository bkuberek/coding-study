import cs.support.*;

public class Solution {
    public ListNode mergeKLists(ListNode[] lists) {
        ListNode merged = null;
        for (ListNode head : lists) {
            merged = merge(merged, head);
        }
        return merged;
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
