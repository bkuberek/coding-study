pub fn max_profit(prices: Vec<i32>) -> i32 {
    // The three end-of-day states of the previous day: holding a share, just sold, resting.
    let (mut hold, mut sold, mut rest) = (-prices[0], 0, 0);
    for &price in &prices[1..] {
        (hold, sold, rest) = (hold.max(rest - price), hold + price, rest.max(sold));
    }
    sold.max(rest)
}
