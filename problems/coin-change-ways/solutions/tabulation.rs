pub fn change(amount: i32, coins: Vec<i32>) -> i32 {
    let amount = amount as usize;
    // ways[i][total] is the number of combinations for `total` using only coins[..i].
    let mut ways = vec![vec![0; amount + 1]; coins.len() + 1];
    ways[0][0] = 1;
    for (i, &coin) in coins.iter().enumerate() {
        let coin = coin as usize;
        for total in 0..=amount {
            // Combinations without this coin, plus those that use it at least once.
            ways[i + 1][total] = ways[i][total];
            if total >= coin {
                ways[i + 1][total] += ways[i + 1][total - coin];
            }
        }
    }
    ways[coins.len()][amount]
}
