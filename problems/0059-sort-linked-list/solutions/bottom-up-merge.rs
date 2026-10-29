use cs_support::ListNode;

pub fn sort_list(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    let length = std::iter::successors(head.as_deref(), |node| node.next.as_deref()).count();
    let mut list = head;
    let mut width = 1;
    // After the pass with width w, the list is a sequence of sorted runs of length 2w.
    while width < length {
        let mut rest = list.take();
        let mut dummy = ListNode::new(0);
        let mut tail = &mut dummy;
        while rest.is_some() {
            let left = cut_run(&mut rest, width);
            let right = cut_run(&mut rest, width);
            tail = merge_onto(tail, left, right);
        }
        list = dummy.next;
        width *= 2;
    }
    list
}

/// Detaches the first `size` nodes from `rest`, which keeps the remaining nodes. Nodes move
/// one at a time, so the cut costs O(size) like the walk it replaces.
fn cut_run(rest: &mut Option<Box<ListNode>>, size: usize) -> Option<Box<ListNode>> {
    let mut run = ListNode::new(0);
    let mut tail = &mut run;
    for _ in 0..size {
        let Some(mut node) = rest.take() else { break };
        *rest = node.next.take();
        tail = tail.next.insert(node);
    }
    run.next
}

/// Appends the merge of two sorted runs after `tail` and returns the new tail.
fn merge_onto(
    mut tail: &mut ListNode,
    mut left: Option<Box<ListNode>>,
    mut right: Option<Box<ListNode>>,
) -> &mut ListNode {
    while let (Some(l), Some(r)) = (&left, &right) {
        let source = if l.val <= r.val {
            &mut left
        } else {
            &mut right
        };
        let mut node = source.take().expect("both runs are non-empty");
        *source = node.next.take();
        tail = tail.next.insert(node);
    }
    tail.next = left.or(right);
    while tail.next.is_some() {
        tail = tail
            .next
            .as_deref_mut()
            .expect("checked by the loop condition");
    }
    tail
}
