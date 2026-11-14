import cs.support.*;
import java.util.*;

public class Solution {
    public ListNode reverseList(ListNode head) {
        Deque<Integer> values = new ArrayDeque<>();
        for (ListNode node = head; node != null; node = node.next) {
            values.push(node.val);
        }
        // Second pass: the stack hands the values back last in, first out.
        for (ListNode node = head; node != null; node = node.next) {
            node.val = values.pop();
        }
        return head;
    }
}
