use std::collections::VecDeque;

use cs_support::ListNode;

pub fn reorder_list(head: &mut Option<Box<ListNode>>) {
    // A Box list has one owner per node, so the "array of nodes" holds the detached nodes.
    let mut nodes = VecDeque::new();
    let mut rest = head.take();
    while let Some(mut node) = rest {
        rest = node.next.take();
        nodes.push_back(node);
    }
    // Alternate: front node -> back node -> next front node, until the nodes run out.
    let mut order = Vec::with_capacity(nodes.len());
    while let Some(front) = nodes.pop_front() {
        order.push(front);
        order.extend(nodes.pop_back());
    }
    // Relink from the last node to the first, so each node takes over its successor.
    let mut list = None;
    for mut node in order.into_iter().rev() {
        node.next = list;
        list = Some(node);
    }
    *head = list;
}
