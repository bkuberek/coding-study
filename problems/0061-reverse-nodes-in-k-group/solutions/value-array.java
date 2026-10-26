import cs.support.*;
import java.util.*;

public class Solution {
    public ListNode reverseKGroup(ListNode head, int k) {
        List<Integer> values = new ArrayList<>();
        for (ListNode node = head; node != null; node = node.next) {
            values.add(node.val);
        }
        // Reverse every full chunk in place; a shorter chunk at the end keeps its order.
        for (int start = 0; start + k <= values.size(); start += k) {
            Collections.reverse(values.subList(start, start + k));
        }
        Iterator<Integer> grouped = values.iterator();
        for (ListNode node = head; node != null; node = node.next) {
            node.val = grouped.next();
        }
        return head;
    }
}
