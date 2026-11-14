import cs.support.*;
import java.math.BigInteger;

public class Solution {
    public ListNode addTwoNumbers(ListNode l1, ListNode l2) {
        String sum = toBigInteger(l1).add(toBigInteger(l2)).toString();
        ListNode dummy = new ListNode();
        ListNode tail = dummy;
        // The decimal string is most significant first; the list wants the opposite order.
        for (int index = sum.length() - 1; index >= 0; index--) {
            tail.next = new ListNode(sum.charAt(index) - '0');
            tail = tail.next;
        }
        return dummy.next;
    }

    private static BigInteger toBigInteger(ListNode head) {
        StringBuilder digits = new StringBuilder();
        for (ListNode node = head; node != null; node = node.next) {
            digits.append(node.val);
        }
        return new BigInteger(digits.reverse().toString());
    }
}
