use cs_support::ListNode;

pub fn reverse_k_group(head: Option<Box<ListNode>>, k: i32) -> Option<Box<ListNode>> {
    let k = k as usize;
    let mut dummy = Box::new(ListNode::new(0));
    let mut tail = &mut dummy;
    let mut rest = head;
    let mut stack: Vec<Box<ListNode>> = Vec::with_capacity(k);
    loop {
        // Take up to k nodes; popping them off the stack yields the group reversed.
        while stack.len() < k {
            let Some(mut node) = rest.take() else { break };
            rest = node.next.take();
            stack.push(node);
        }
        if stack.len() < k {
            // A short tail keeps its order.
            for node in stack {
                tail = tail.next.insert(node);
            }
            return dummy.next;
        }
        while let Some(node) = stack.pop() {
            tail = tail.next.insert(node);
        }
    }
}
