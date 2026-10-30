pub fn change(amount: i32, coins: Vec<i32>) -> i32 {
    let amount = amount as usize;
    // After processing a prefix of the coins, ways[total] counts the combinations for `total`
    // that use only those coins.
    let mut ways = vec![0; amount + 1];
    ways[0] = 1;
    for &coin in &coins {
        let coin = coin as usize;
        // Increasing totals: ways[total - coin] already allows this coin, so it can repeat.
        for total in coin..=amount {
            ways[total] += ways[total - coin];
        }
    }
    ways[amount]
}
