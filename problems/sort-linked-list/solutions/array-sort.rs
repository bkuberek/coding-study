use cs_support::ListNode;

pub fn sort_list(mut head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    let mut values: Vec<i32> = std::iter::successors(head.as_deref(), |node| node.next.as_deref())
        .map(|node| node.val)
        .collect();
    values.sort_unstable();
    // Write the sorted values back into the same nodes, in list order.
    let mut node = head.as_deref_mut();
    for value in values {
        let Some(current) = node else { break };
        current.val = value;
        node = current.next.as_deref_mut();
    }
    head
}
