use cs_support::ListNode;

pub fn sort_list(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    let mut sorted: Option<Box<ListNode>> = None; // the sorted prefix
    let mut rest = head;
    while let Some(mut node) = rest {
        rest = node.next.take();
        // Find the last sorted node whose value is smaller, and insert after it.
        let mut spot = &mut sorted;
        while spot.as_ref().is_some_and(|next| next.val < node.val) {
            spot = &mut spot.as_mut().expect("checked by the loop condition").next;
        }
        node.next = spot.take();
        *spot = Some(node);
    }
    sorted
}
