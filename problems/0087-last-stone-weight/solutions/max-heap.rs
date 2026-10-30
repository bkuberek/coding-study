use std::collections::BinaryHeap;

pub fn last_stone_weight(stones: Vec<i32>) -> i32 {
    let mut heap = BinaryHeap::from(stones);
    while heap.len() > 1 {
        let heaviest = heap.pop().expect("at least two stones");
        let second = heap.pop().expect("at least two stones");
        if heaviest != second {
            heap.push(heaviest - second);
        }
    }
    heap.peek().copied().unwrap_or(0)
}
