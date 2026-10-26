import cs.support.*;
import java.util.*;

public class Solution {
    public void reorderList(ListNode head) {
        List<ListNode> nodes = new ArrayList<>();
        for (ListNode node = head; node != null; node = node.next) {
            nodes.add(node);
        }
        if (nodes.isEmpty()) {
            return;
        }
        int left = 0;
        int right = nodes.size() - 1;
        // Alternate: front node -> back node -> next front node, until the indexes meet.
        while (left < right) {
            nodes.get(left).next = nodes.get(right);
            left++;
            if (left == right) {
                break;
            }
            nodes.get(right).next = nodes.get(left);
            right--;
        }
        nodes.get(left).next = null;
    }
}
