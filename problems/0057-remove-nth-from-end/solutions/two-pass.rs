use cs_support::ListNode;

pub fn remove_nth_from_end(head: Option<Box<ListNode>>, n: i32) -> Option<Box<ListNode>> {
    let length = std::iter::successors(head.as_deref(), |node| node.next.as_deref()).count();
    // The dummy node is the predecessor of the head, so removing the head is not special.
    let mut dummy = ListNode { val: 0, next: head };
    let mut before = &mut dummy;
    for _ in 0..length - n as usize {
        before = before
            .next
            .as_deref_mut()
            .expect("the node before the target exists");
    }
    let removed = before.next.take().expect("the target node exists");
    before.next = removed.next;
    dummy.next
}
