pub fn is_n_straight_hand(hand: Vec<i32>, group_size: i32) -> bool {
    if hand.len() % group_size as usize != 0 {
        return false;
    }
    let mut cards = hand;
    cards.sort_unstable();
    while !cards.is_empty() {
        // The smallest card must start a straight; remove that straight card by card.
        let smallest = cards.remove(0);
        for value in smallest + 1..smallest + group_size {
            match cards.iter().position(|&card| card == value) {
                Some(index) => {
                    cards.remove(index);
                }
                None => return false,
            }
        }
    }
    true
}
