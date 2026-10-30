pub fn coin_change(coins: Vec<i32>, amount: i32) -> i32 {
    // Remainders are nodes; paying one coin is an edge. The first level that reaches 0 is
    // the fewest number of coins.
    let amount = amount as usize;
    let mut seen = vec![false; amount + 1];
    seen[amount] = true;
    let mut level = vec![amount];
    let mut coins_used = 0;
    while !level.is_empty() {
        if seen[0] {
            return coins_used;
        }
        let mut next_level = Vec::new();
        for &remaining in &level {
            for &coin in &coins {
                if let Some(rest) = remaining.checked_sub(coin as usize) {
                    if !seen[rest] {
                        seen[rest] = true;
                        next_level.push(rest);
                    }
                }
            }
        }
        level = next_level;
        coins_used += 1;
    }
    -1
}
