use cs_support::ListNode;

pub fn copy_list(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    let mut values = Vec::new();
    let mut node = head.as_deref();
    while let Some(current) = node {
        values.push(current.val);
        node = current.next.as_deref();
    }
    let mut copy = None;
    for val in values.into_iter().rev() {
        copy = Some(Box::new(ListNode { val, next: copy }));
    }
    copy
}
