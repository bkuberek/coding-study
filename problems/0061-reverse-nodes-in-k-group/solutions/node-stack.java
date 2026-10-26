import cs.support.*;
import java.util.*;

public class Solution {
    public ListNode reverseKGroup(ListNode head, int k) {
        ListNode dummy = new ListNode();
        ListNode tail = dummy;
        ListNode node = head;
        Deque<ListNode> stack = new ArrayDeque<>();
        while (true) {
            // Take up to k nodes; popping them off the stack yields the group reversed.
            ListNode probe = node;
            while (probe != null && stack.size() < k) {
                stack.push(probe);
                probe = probe.next;
            }
            if (stack.size() < k) {
                tail.next = node; // a short tail keeps its order
                return dummy.next;
            }
            while (!stack.isEmpty()) {
                tail.next = stack.pop();
                tail = tail.next;
            }
            node = probe;
        }
    }
}
