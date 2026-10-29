use cs_support::ListNode;

pub fn merge_two_lists(
    list1: Option<Box<ListNode>>,
    list2: Option<Box<ListNode>>,
) -> Option<Box<ListNode>> {
    match (list1, list2) {
        (None, rest) | (rest, None) => rest,
        // The smaller head starts the merged list; the merge of everything else follows it.
        (Some(mut first), Some(mut second)) => {
            if first.val <= second.val {
                first.next = merge_two_lists(first.next.take(), Some(second));
                Some(first)
            } else {
                second.next = merge_two_lists(Some(first), second.next.take());
                Some(second)
            }
        }
    }
}
