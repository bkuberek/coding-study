use cs_support::ListNode;

pub fn merge_k_lists(lists: Vec<Option<Box<ListNode>>>) -> Option<Box<ListNode>> {
    lists.into_iter().fold(None, merge)
}

fn merge(
    mut left: Option<Box<ListNode>>,
    mut right: Option<Box<ListNode>>,
) -> Option<Box<ListNode>> {
    let mut dummy = Box::new(ListNode::new(0));
    let mut tail = &mut dummy;
    while let (Some(l), Some(r)) = (&left, &right) {
        let source = if l.val <= r.val {
            &mut left
        } else {
            &mut right
        };
        let mut node = source.take().expect("both lists are non-empty");
        *source = node.next.take();
        tail = tail.next.insert(node);
    }
    tail.next = left.or(right);
    dummy.next
}
