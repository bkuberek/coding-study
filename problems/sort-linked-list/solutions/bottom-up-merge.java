import cs.support.*;

public class Solution {
    public ListNode sortList(ListNode head) {
        int length = 0;
        for (ListNode node = head; node != null; node = node.next) {
            length++;
        }
        ListNode dummy = new ListNode(0, head);
        // After the pass with width w, the list is a sequence of sorted runs of length 2w.
        for (int width = 1; width < length; width *= 2) {
            ListNode tail = dummy;
            ListNode rest = dummy.next;
            while (rest != null) {
                ListNode left = rest;
                ListNode right = cutAfter(left, width);
                rest = cutAfter(right, width);
                tail = mergeOnto(tail, left, right);
            }
        }
        return dummy.next;
    }

    /** Detach the first {@code size} nodes from the rest and return the rest's head. */
    private static ListNode cutAfter(ListNode head, int size) {
        ListNode node = head;
        for (int step = 1; step < size && node != null; step++) {
            node = node.next;
        }
        if (node == null) {
            return null;
        }
        ListNode rest = node.next;
        node.next = null;
        return rest;
    }

    /** Append the merge of two sorted runs after {@code tail} and return the new tail. */
    private static ListNode mergeOnto(ListNode tail, ListNode left, ListNode right) {
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
        while (tail.next != null) {
            tail = tail.next;
        }
        return tail;
    }
}
