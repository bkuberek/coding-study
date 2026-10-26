package cs.support;

/** A singly linked list node, as on LeetCode. JSON: {@code [1, 2, 3]}; {@code []} is null. */
public class ListNode {
    public int val;
    public ListNode next;

    public ListNode() {
    }

    public ListNode(int val) {
        this.val = val;
    }

    public ListNode(int val, ListNode next) {
        this.val = val;
        this.next = next;
    }
}
