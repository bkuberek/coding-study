use cs_support::ListNode;

pub fn reverse_list(mut head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    let mut values = Vec::new();
    let mut node = &head;
    while let Some(current) = node {
        values.push(current.val);
        node = &current.next;
    }
    // Second pass: the same nodes, in the same order, receive the values from the back.
    let mut node = &mut head;
    while let Some(current) = node {
        current.val = values.pop().unwrap();
        node = &mut current.next;
    }
    head
}
