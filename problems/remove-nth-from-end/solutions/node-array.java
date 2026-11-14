import cs.support.*;
import java.util.*;

public class Solution {
    public ListNode removeNthFromEnd(ListNode head, int n) {
        List<ListNode> nodes = new ArrayList<>();
        for (ListNode node = head; node != null; node = node.next) {
            nodes.add(node);
        }
        int target = nodes.size() - n;
        if (target == 0) {
            return nodes.get(0).next;
        }
        nodes.get(target - 1).next = nodes.get(target).next;
        return head;
    }
}
