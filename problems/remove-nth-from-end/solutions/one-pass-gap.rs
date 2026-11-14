use cs_support::ListNode;

pub fn remove_nth_from_end(head: Option<Box<ListNode>>, n: i32) -> Option<Box<ListNode>> {
    let mut dummy = ListNode { val: 0, next: head };
    // `lead` starts n + 1 nodes ahead of `trail`; when `lead` falls off the end, `trail` sits
    // just before the node to remove. `lead` only reads, so it is a shared cursor. `trail` would
    // be a `&mut` into the same list, which Rust rejects while `lead` borrows it, so count how
    // far `trail` moves and replay that many steps with the `&mut` cursor afterwards.
    let mut lead = Some(&dummy);
    for _ in 0..=n {
        lead = lead.and_then(|node| node.next.as_deref());
    }
    let mut trail_steps = 0;
    while let Some(node) = lead {
        lead = node.next.as_deref();
        trail_steps += 1;
    }
    let mut trail = &mut dummy;
    for _ in 0..trail_steps {
        trail = trail
            .next
            .as_deref_mut()
            .expect("trail stays inside the list");
    }
    let removed = trail.next.take().expect("the target node exists");
    trail.next = removed.next;
    dummy.next
}
