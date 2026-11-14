use cs_support::ListNode;

pub fn reverse_list(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    reverse_onto(head, None)
}

/// Reverses `rest` and puts it in front of `reversed`, which already holds the nodes that came
/// before `rest` in reverse order. Each call moves one node, so the depth is the list length.
fn reverse_onto(
    rest: Option<Box<ListNode>>,
    reversed: Option<Box<ListNode>>,
) -> Option<Box<ListNode>> {
    match rest {
        None => reversed,
        Some(mut node) => {
            let following = node.next.take();
            node.next = reversed;
            reverse_onto(following, Some(node))
        }
    }
}
