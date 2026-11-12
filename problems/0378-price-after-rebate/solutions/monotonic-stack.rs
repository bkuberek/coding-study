pub fn prices_after_rebate(prices: Vec<i32>) -> Vec<i32> {
    let mut paid = prices.clone();
    // Slots still waiting for a rebate; their prices rise strictly from bottom to top.
    let mut waiting: Vec<usize> = Vec::new();
    for (slot, &price) in prices.iter().enumerate() {
        while let Some(&earlier) = waiting.last() {
            if prices[earlier] < price {
                break;
            }
            waiting.pop();
            paid[earlier] = prices[earlier] - price;
        }
        waiting.push(slot);
    }
    paid
}
