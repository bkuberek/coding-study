use cs_support::ListNode;

pub fn reverse_k_group(mut head: Option<Box<ListNode>>, k: i32) -> Option<Box<ListNode>> {
    let mut values: Vec<i32> = std::iter::successors(head.as_deref(), |node| node.next.as_deref())
        .map(|node| node.val)
        .collect();
    // Reverse every full chunk; a shorter chunk at the end keeps its order.
    for chunk in values.chunks_exact_mut(k as usize) {
        chunk.reverse();
    }
    let mut node = head.as_deref_mut();
    for value in values {
        let Some(current) = node else { break };
        current.val = value;
        node = current.next.as_deref_mut();
    }
    head
}
