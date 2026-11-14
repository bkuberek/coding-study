import cs.support.*;
import java.util.*;

public class Solution {
    public boolean hasCycle(ListNode head) {
        // ListNode does not override equals, so the set compares node identities.
        Set<ListNode> visited = new HashSet<>();
        for (ListNode node = head; node != null; node = node.next) {
            if (!visited.add(node)) {
                return true;
            }
        }
        return false;
    }
}
