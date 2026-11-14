pub fn prices_after_rebate(prices: Vec<i32>) -> Vec<i32> {
    let mut paid = prices.clone();
    for slot in 0..prices.len() {
        if let Some(offset) = prices[slot + 1..].iter().position(|&later| later <= prices[slot]) {
            paid[slot] = prices[slot] - prices[slot + 1 + offset];
        }
    }
    paid
}
