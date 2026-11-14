use cs_support::ListNode;

pub fn reorder_list(head: &mut Option<Box<ListNode>>) {
    let Some(mut current) = head.as_mut() else {
        return;
    };
    // Each round moves the current tail right after `current`; two or fewer nodes from
    // `current` onward are already in their final order.
    while current
        .next
        .as_ref()
        .is_some_and(|next| next.next.is_some())
    {
        let mut tail = pop_tail(&mut current.next).expect("at least two nodes follow");
        tail.next = current.next.take();
        current.next = Some(tail);
        // Skip `current` and the tail just placed behind it.
        current = current
            .next
            .as_mut()
            .and_then(|tail| tail.next.as_mut())
            .expect("the old successor follows the tail");
    }
}

/// Detaches the last node: the walk is O(length), as in the other languages.
fn pop_tail(list: &mut Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    let mut cursor = list;
    while cursor.as_ref()?.next.is_some() {
        cursor = &mut cursor.as_mut()?.next;
    }
    cursor.take()
}
