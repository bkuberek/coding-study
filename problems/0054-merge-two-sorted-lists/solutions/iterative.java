import cs.support.*;

public class Solution {
    public ListNode mergeTwoLists(ListNode list1, ListNode list2) {
        // The dummy node gives the merged list a fixed place to start, so the first splice
        // needs no special case.
        ListNode dummy = new ListNode();
        ListNode tail = dummy;
        while (list1 != null && list2 != null) {
            if (list1.val <= list2.val) {
                tail.next = list1;
                list1 = list1.next;
            } else {
                tail.next = list2;
                list2 = list2.next;
            }
            tail = tail.next;
        }
        // At most one list has nodes left, and they are already sorted: link them as a block.
        tail.next = list1 != null ? list1 : list2;
        return dummy.next;
    }
}
