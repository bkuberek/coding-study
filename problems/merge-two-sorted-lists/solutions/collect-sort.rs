use cs_support::ListNode;

pub fn merge_two_lists(
    list1: Option<Box<ListNode>>,
    list2: Option<Box<ListNode>>,
) -> Option<Box<ListNode>> {
    let mut values = Vec::new();
    for list in [&list1, &list2] {
        let mut node = list;
        while let Some(current) = node {
            values.push(current.val);
            node = &current.next;
        }
    }
    values.sort_unstable();
    // Build the new list from its last node to its first, so each node owns the rest.
    let mut merged = None;
    for &value in values.iter().rev() {
        merged = Some(Box::new(ListNode {
            val: value,
            next: merged,
        }));
    }
    merged
}
