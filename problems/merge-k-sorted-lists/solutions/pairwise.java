import cs.support.*;

public class Solution {
    public ListNode mergeKLists(ListNode[] lists) {
        if (lists.length == 0) {
            return null;
        }
        // Each round merges neighbours (0 with 1, 2 with 3, ...), halving the number of lists;
        // every node takes part in one merge per round, and there are ceil(log2 k) rounds.
        ListNode[] heads = lists;
        while (heads.length > 1) {
            ListNode[] next = new ListNode[(heads.length + 1) / 2];
            for (int index = 0; index < heads.length; index += 2) {
                ListNode partner = index + 1 < heads.length ? heads[index + 1] : null;
                next[index / 2] = merge(heads[index], partner);
            }
            heads = next;
        }
        return heads[0];
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
