use std::cmp::Reverse;
use std::collections::binary_heap::PeekMut;
use std::collections::BinaryHeap;

use cs_support::ListNode;

pub fn merge_k_lists(mut lists: Vec<Option<Box<ListNode>>>) -> Option<Box<ListNode>> {
    // `BinaryHeap` is a max-heap, so `Reverse` makes it a min-heap. Entries are (value, list
    // index): the index breaks ties and names the list whose first node the entry stands for.
    // The nodes themselves stay in `lists`, each list holding the nodes not merged yet.
    let mut heap: BinaryHeap<Reverse<(i32, usize)>> = lists
        .iter()
        .enumerate()
        .filter_map(|(index, head)| head.as_ref().map(|node| Reverse((node.val, index))))
        .collect();
    let mut dummy = Box::new(ListNode::new(0));
    let mut tail = &mut dummy;
    while let Some(mut top) = heap.peek_mut() {
        let Reverse((_, index)) = *top;
        let mut node = lists[index]
            .take()
            .expect("a heap entry names a non-empty list");
        lists[index] = node.next.take();
        tail = tail.next.insert(node);
        match &lists[index] {
            // Replace the root in place; dropping `top` sifts the new entry down.
            Some(next) => *top = Reverse((next.val, index)),
            None => {
                PeekMut::pop(top);
            }
        }
    }
    dummy.next
}
