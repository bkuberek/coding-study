use cs_support::ListNode;

pub fn remove_nth_from_end(head: Option<Box<ListNode>>, n: i32) -> Option<Box<ListNode>> {
    // A Box list has one owner per node, so the array holds the detached nodes.
    let mut nodes = Vec::new();
    let mut rest = head;
    while let Some(mut node) = rest {
        rest = node.next.take();
        nodes.push(node);
    }
    nodes.remove(nodes.len() - n as usize);
    // Relink from the last node to the first, so each node takes over its successor.
    let mut list = None;
    for mut node in nodes.into_iter().rev() {
        node.next = list;
        list = Some(node);
    }
    list
}
