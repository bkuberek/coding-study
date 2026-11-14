pub fn max_profit(prices: Vec<i32>) -> i32 {
    let mut cheapest = prices[0];
    let mut best = 0;
    for &price in &prices {
        // Selling today, the best purchase is the cheapest earlier day (or today: profit 0).
        best = best.max(price - cheapest);
        cheapest = cheapest.min(price);
    }
    best
}
