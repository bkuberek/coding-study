import cs.support.*;
import java.util.*;

public class Solution {
    public ListNode mergeKLists(ListNode[] lists) {
        // PriorityQueue is a min-heap; the comparator orders nodes by value.
        PriorityQueue<ListNode> heap = new PriorityQueue<>(Comparator.comparingInt(node -> node.val));
        for (ListNode head : lists) {
            if (head != null) {
                heap.offer(head);
            }
        }
        ListNode dummy = new ListNode();
        ListNode tail = dummy;
        while (!heap.isEmpty()) {
            ListNode node = heap.poll();
            tail.next = node;
            tail = node;
            if (node.next != null) {
                heap.offer(node.next);
            }
        }
        return dummy.next;
    }
}
