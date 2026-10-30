pub fn last_stone_weight(stones: Vec<i32>) -> i32 {
    let mut remaining = stones;
    while remaining.len() > 1 {
        remaining.sort();
        let heaviest = remaining.pop().expect("at least two stones");
        let second = remaining.pop().expect("at least two stones");
        if heaviest != second {
            remaining.push(heaviest - second);
        }
    }
    remaining.first().copied().unwrap_or(0)
}
