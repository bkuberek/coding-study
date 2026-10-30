pub fn change(amount: i32, coins: Vec<i32>) -> i32 {
    let amount = amount as usize;
    let coins: Vec<usize> = coins.iter().map(|&coin| coin as usize).collect();
    // ways[i][total] caches the combinations for `total` using coins[i..]; None is unknown.
    let mut ways = vec![vec![None; amount + 1]; coins.len()];
    count(0, amount, &coins, &mut ways)
}

fn count(i: usize, total: usize, coins: &[usize], ways: &mut [Vec<Option<i32>>]) -> i32 {
    if total == 0 {
        return 1;
    }
    if i == coins.len() {
        return 0;
    }
    if let Some(known) = ways[i][total] {
        return known;
    }
    // Either no coin of value coins[i] is used, or at least one is.
    let skip = count(i + 1, total, coins, ways);
    let used = if coins[i] <= total {
        count(i, total - coins[i], coins, ways)
    } else {
        0
    };
    ways[i][total] = Some(skip + used);
    skip + used
}
