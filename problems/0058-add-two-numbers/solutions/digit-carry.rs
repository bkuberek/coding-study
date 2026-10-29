use cs_support::ListNode;

pub fn add_two_numbers(
    l1: Option<Box<ListNode>>,
    l2: Option<Box<ListNode>>,
) -> Option<Box<ListNode>> {
    let mut dummy = Box::new(ListNode::new(0));
    let mut tail = &mut dummy;
    let (mut l1, mut l2) = (l1.as_deref(), l2.as_deref());
    let mut carry = 0;
    // Keep going while either number has digits left or a carry is still pending.
    while l1.is_some() || l2.is_some() || carry > 0 {
        let mut total = carry;
        if let Some(node) = l1 {
            total += node.val;
            l1 = node.next.as_deref();
        }
        if let Some(node) = l2 {
            total += node.val;
            l2 = node.next.as_deref();
        }
        carry = total / 10;
        tail = tail.next.insert(Box::new(ListNode::new(total % 10)));
    }
    dummy.next
}
