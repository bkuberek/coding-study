use std::collections::{HashMap, VecDeque};

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
    // Straights started but not yet complete; each needs the current value.
    let mut open_count = 0;
    // Straights opened at each of the last group_size values.
    let mut opened: VecDeque<i32> = VecDeque::new();
    let mut previous = 0;
    for value in values {
        if open_count > 0 && value != previous + 1 {
            return false; // an open straight needs previous + 1, which is missing
        }
        if counts[&value] < open_count {
            return false;
        }
        let started = counts[&value] - open_count;
        opened.push_back(started);
        open_count += started;
        if opened.len() == group_size as usize {
            // The straights opened group_size values ago end with this value.
            open_count -= opened.pop_front().unwrap_or(0);
        }
        previous = value;
    }
    open_count == 0
}
