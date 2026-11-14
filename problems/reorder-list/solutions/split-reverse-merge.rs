use cs_support::ListNode;

pub fn reorder_list(head: &mut Option<Box<ListNode>>) {
    // 1. Find the end of the front half: for n nodes, it is node (n - 1) / 2. Two cursors into
    // one Box list cannot both be `&mut`, so count the nodes first and walk a single cursor.
    let length = std::iter::successors(head.as_deref(), |node| node.next.as_deref()).count();
    if length < 2 {
        return;
    }
    let mut cursor = head.as_mut();
    for _ in 0..(length - 1) / 2 {
        cursor = cursor.and_then(|node| node.next.as_mut());
    }
    // 2. Cut the list and reverse the back half.
    let mut back = reverse(cursor.and_then(|node| node.next.take()));
    // 3. Interleave; the front half is never shorter than the back half.
    let mut front = head.as_deref_mut();
    while let (Some(front_node), Some(mut back_node)) = (front, back.take()) {
        back = back_node.next.take();
        back_node.next = front_node.next.take();
        front_node.next = Some(back_node);
        front = front_node
            .next
            .as_mut()
            .and_then(|node| node.next.as_deref_mut());
    }
}

fn reverse(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    let mut previous = None;
    let mut current = head;
    while let Some(mut node) = current {
        current = node.next.take();
        node.next = previous;
        previous = Some(node);
    }
    previous
}
