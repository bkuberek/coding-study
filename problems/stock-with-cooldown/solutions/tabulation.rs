pub fn max_profit(prices: Vec<i32>) -> i32 {
    let n = prices.len();
    // Best profit at the end of day i when:
    //   hold[i]: a share is held; sold[i]: a share was sold on day i;
    //   rest[i]: no share is held and none was sold on day i (free to buy tomorrow).
    let mut hold = vec![0; n];
    let mut sold = vec![0; n];
    let mut rest = vec![0; n];
    hold[0] = -prices[0];
    for i in 1..n {
        hold[i] = hold[i - 1].max(rest[i - 1] - prices[i]);
        sold[i] = hold[i - 1] + prices[i];
        rest[i] = rest[i - 1].max(sold[i - 1]);
    }
    sold[n - 1].max(rest[n - 1])
}
