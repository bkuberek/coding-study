use std::collections::HashMap;

pub fn is_n_straight_hand(hand: Vec<i32>, group_size: i32) -> bool {
    if hand.len() % group_size as usize != 0 {
        return false;
    }
    let mut counts: HashMap<i32, i32> = HashMap::with_capacity(hand.len());
    for &card in &hand {
        *counts.entry(card).or_insert(0) += 1;
    }
    let mut values: Vec<i32> = counts.keys().copied().collect();
    values.sort_unstable();
    for value in values {
        let starting = counts[&value];
        if starting == 0 {
            continue;
        }
        // Every card left at the smallest remaining value starts its own straight.
        for following in value..value + group_size {
            match counts.get_mut(&following) {
                Some(count) if *count >= starting => *count -= starting,
                _ => return false,
            }
        }
    }
    true
}
