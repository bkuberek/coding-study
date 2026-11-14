import cs.support.*;
import java.util.*;

public class Solution {
    public ListNode mergeTwoLists(ListNode list1, ListNode list2) {
        List<Integer> values = new ArrayList<>();
        for (ListNode start : new ListNode[] {list1, list2}) {
            for (ListNode node = start; node != null; node = node.next) {
                values.add(node.val);
            }
        }
        Collections.sort(values);
        ListNode dummy = new ListNode();
        ListNode tail = dummy;
        for (int value : values) {
            tail.next = new ListNode(value);
            tail = tail.next;
        }
        return dummy.next;
    }
}
