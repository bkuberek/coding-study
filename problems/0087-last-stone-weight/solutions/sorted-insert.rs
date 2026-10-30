pub fn last_stone_weight(stones: Vec<i32>) -> i32 {
    let mut remaining = stones;
    remaining.sort();
    while remaining.len() > 1 {
        let heaviest = remaining.pop().expect("at least two stones");
        let second = remaining.pop().expect("at least two stones");
        if heaviest != second {
            let leftover = heaviest - second;
            // Binary search finds the slot in O(log n); shifting the tail to open it is O(n).
            let position = remaining.partition_point(|&weight| weight < leftover);
            remaining.insert(position, leftover);
        }
    }
    remaining.first().copied().unwrap_or(0)
}
