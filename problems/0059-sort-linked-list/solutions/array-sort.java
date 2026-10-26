import cs.support.*;
import java.util.*;

public class Solution {
    public ListNode sortList(ListNode head) {
        int length = 0;
        for (ListNode node = head; node != null; node = node.next) {
            length++;
        }
        int[] values = new int[length];
        int index = 0;
        for (ListNode node = head; node != null; node = node.next) {
            values[index++] = node.val;
        }
        Arrays.sort(values);
        // Write the sorted values back into the same nodes, in list order.
        index = 0;
        for (ListNode node = head; node != null; node = node.next) {
            node.val = values[index++];
        }
        return head;
    }
}
