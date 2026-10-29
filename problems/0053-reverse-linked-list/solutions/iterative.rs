use cs_support::ListNode;

pub fn reverse_list(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    let mut previous = None;
    let mut current = head;
    while let Some(mut node) = current {
        // Take the rest of the list out before the link that leads to it is redirected.
        current = node.next.take();
        node.next = previous;
        previous = Some(node);
    }
    previous
}
