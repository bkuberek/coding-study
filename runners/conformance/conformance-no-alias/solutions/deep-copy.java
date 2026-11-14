import cs.support.*;
import java.util.*;

public class Solution {
    public ListNode copyList(ListNode head) {
        ListNode sentinel = new ListNode();
        ListNode tail = sentinel;
        for (ListNode node = head; node != null; node = node.next) {
            tail.next = new ListNode(node.val);
            tail = tail.next;
        }
        return sentinel.next;
    }
}
