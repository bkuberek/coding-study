use cs_support::ListNode;

pub fn merge_two_lists(
    mut list1: Option<Box<ListNode>>,
    mut list2: Option<Box<ListNode>>,
) -> Option<Box<ListNode>> {
    // The dummy node gives the merged list a fixed place to start, so the first splice
    // needs no special case.
    let mut dummy = Box::new(ListNode::new(0));
    let mut tail = &mut dummy;
    while let (Some(first), Some(second)) = (&list1, &list2) {
        let smaller = if first.val <= second.val {
            &mut list1
        } else {
            &mut list2
        };
        // Detach the smaller head from its list and link it behind the tail.
        let mut node = smaller.take().unwrap();
        *smaller = node.next.take();
        tail.next = Some(node);
        tail = tail.next.as_mut().unwrap();
    }
    // At most one list has nodes left, and they are already sorted: link them as a block.
    tail.next = list1.or(list2);
    dummy.next
}
