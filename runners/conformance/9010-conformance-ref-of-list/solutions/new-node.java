import cs.support.*;
import java.util.*;

public class Solution {
    public ListNode pickNode(ListNode head, ListNode node) {
        return node == null ? null : new ListNode(node.val);
    }
}
