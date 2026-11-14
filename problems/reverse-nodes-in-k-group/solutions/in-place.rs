use cs_support::ListNode;

pub fn reverse_k_group(head: Option<Box<ListNode>>, k: i32) -> Option<Box<ListNode>> {
    let k = k as usize;
    let mut dummy = ListNode { val: 0, next: head };
    let mut before = &mut dummy; // the node just before the next group
    loop {
        // Fewer than k nodes remain: leave them as they are.
        let group_end =
            std::iter::successors(before.next.as_deref(), |node| node.next.as_deref()).nth(k - 1);
        if group_end.is_none() {
            break;
        }
        // Reverse the group by moving its nodes one by one onto a new list.
        let mut current = before.next.take();
        let mut reversed = None;
        for _ in 0..k {
            let mut node = current.take().expect("k nodes remain");
            current = node.next.take();
            node.next = reversed;
            reversed = Some(node);
        }
        before.next = reversed;
        // The group's first node is now its last: walk to it and point it at the rest.
        for _ in 0..k {
            before = before.next.as_deref_mut().expect("the group has k nodes");
        }
        before.next = current;
    }
    dummy.next
}
