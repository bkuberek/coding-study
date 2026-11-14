pub fn max_profit(prices: Vec<i32>) -> i32 {
    // memo[holding][day] is the most profit from `day` on, or None while unknown.
    let mut memo = vec![vec![None; prices.len()]; 2];
    best(0, 0, &prices, &mut memo)
}

fn best(day: usize, holding: usize, prices: &[i32], memo: &mut [Vec<Option<i32>>]) -> i32 {
    if day >= prices.len() {
        return 0;
    }
    if let Some(known) = memo[holding][day] {
        return known;
    }
    let wait = best(day + 1, holding, prices, memo);
    let act = if holding == 1 {
        // Selling today forces tomorrow to be a cooldown day, so resume on day + 2.
        prices[day] + best(day + 2, 0, prices, memo)
    } else {
        -prices[day] + best(day + 1, 1, prices, memo)
    };
    let result = wait.max(act);
    memo[holding][day] = Some(result);
    result
}
