pub fn coin_change(coins: Vec<i32>, amount: i32) -> i32 {
    // fewest[x] is the fewest coins that pay x exactly; amount + 1 means "cannot be paid",
    // since any real answer uses at most `amount` coins.
    let unreachable = amount + 1;
    let amount = amount as usize;
    let mut fewest = vec![unreachable; amount + 1];
    fewest[0] = 0;
    for x in 1..=amount {
        for &coin in &coins {
            let coin = coin as usize;
            if coin <= x && fewest[x - coin] + 1 < fewest[x] {
                fewest[x] = fewest[x - coin] + 1;
            }
        }
    }
    if fewest[amount] == unreachable {
        -1
    } else {
        fewest[amount]
    }
}
