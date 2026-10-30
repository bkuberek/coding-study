use std::collections::BinaryHeap;

pub fn find_maximized_capital(k: i32, mut w: i32, profits: Vec<i32>, capital: Vec<i32>) -> i32 {
    // (capital, profit) pairs, cheapest requirement first.
    let mut projects: Vec<(i32, i32)> = capital.into_iter().zip(profits).collect();
    projects.sort_unstable();
    let mut affordable = BinaryHeap::new();
    let mut unlocked = 0;
    for _ in 0..k {
        // Capital only grows, so every project unlocked once stays affordable.
        while unlocked < projects.len() && projects[unlocked].0 <= w {
            affordable.push(projects[unlocked].1);
            unlocked += 1;
        }
        let Some(profit) = affordable.pop() else {
            break; // nothing affordable now, and capital cannot grow any more
        };
        w += profit;
    }
    w
}
