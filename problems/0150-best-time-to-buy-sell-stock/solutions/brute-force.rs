pub fn max_profit(prices: Vec<i32>) -> i32 {
    let mut best = 0;
    for buy in 0..prices.len() {
        for sell in buy + 1..prices.len() {
            best = best.max(prices[sell] - prices[buy]);
        }
    }
    best
}
