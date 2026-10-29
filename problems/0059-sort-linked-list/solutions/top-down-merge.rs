use cs_support::ListNode;

pub fn sort_list(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    let length = std::iter::successors(head.as_deref(), |node| node.next.as_deref()).count();
    sort_nodes(head, length)
}

/// Sorts a list of `length` nodes. Two cursors into one Box list cannot both be `&mut`, so
/// the split point comes from the length instead of a slow and a fast pointer.
fn sort_nodes(mut head: Option<Box<ListNode>>, length: usize) -> Option<Box<ListNode>> {
    if length < 2 {
        return head;
    }
    // The left half gets the extra node of an odd length, as with `fast = head.next`.
    let left_length = length.div_ceil(2);
    let mut end_of_left = head.as_mut();
    for _ in 1..left_length {
        end_of_left = end_of_left.and_then(|node| node.next.as_mut());
    }
    let right = end_of_left.and_then(|node| node.next.take());
    merge(
        sort_nodes(head, left_length),
        sort_nodes(right, length - left_length),
    )
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
        let mut node = source.take().expect("both runs are non-empty");
        *source = node.next.take();
        tail = tail.next.insert(node);
    }
    tail.next = left.or(right);
    dummy.next
}
