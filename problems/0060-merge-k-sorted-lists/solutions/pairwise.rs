use cs_support::ListNode;

pub fn merge_k_lists(lists: Vec<Option<Box<ListNode>>>) -> Option<Box<ListNode>> {
    // Each round merges neighbours (0 with 1, 2 with 3, ...), halving the number of lists;
    // every node takes part in one merge per round, and there are ceil(log2 k) rounds.
    let mut heads = lists;
    while heads.len() > 1 {
        let mut merged = Vec::with_capacity(heads.len().div_ceil(2));
        let mut pending = heads.into_iter();
        while let Some(left) = pending.next() {
            merged.push(merge(left, pending.next().flatten()));
        }
        heads = merged;
    }
    heads.pop().flatten()
}

fn merge(
    mut left: Option<Box<ListNode>>,
    mut right: Option<Box<ListNode>>,
) -> Option<Box<ListNode>> {
    let mut dummy = Box::new(ListNode::new(0));
    let mut tail = &mut dummy;
    while let (Some(l), Some(r)) = (&left, &right) {
        let source = if l.val <= r.val {
            &mut left
        } else {
            &mut right
        };
        let mut node = source.take().expect("both lists are non-empty");
        *source = node.next.take();
        tail = tail.next.insert(node);
    }
    tail.next = left.or(right);
    dummy.next
}
