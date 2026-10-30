pub fn max_profit(prices: Vec<i32>) -> i32 {
    // A trade from day i to day j earns the sum of the daily changes between them, so the
    // answer is the best sum of a run of consecutive changes (Kadane), or 0.
    let (mut best, mut ending_here) = (0, 0);
    for pair in prices.windows(2) {
        ending_here = (ending_here + pair[1] - pair[0]).max(0);
        best = best.max(ending_here);
    }
    best
}
