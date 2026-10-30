pub fn find_maximized_capital(k: i32, mut w: i32, profits: Vec<i32>, capital: Vec<i32>) -> i32 {
    let mut used = vec![false; profits.len()];
    for _ in 0..k {
        let mut best = None;
        let mut best_profit = -1; // profits are never negative
        for (index, &profit) in profits.iter().enumerate() {
            if !used[index] && capital[index] <= w && profit > best_profit {
                best = Some(index);
                best_profit = profit;
            }
        }
        let Some(best) = best else {
            break; // nothing affordable now, and capital cannot grow any more
        };
        used[best] = true;
        w += profits[best];
    }
    w
}
