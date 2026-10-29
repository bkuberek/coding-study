pub fn mincost_tickets(days: Vec<i32>, costs: Vec<i32>) -> i32 {
    let last_day = days[days.len() - 1] as usize;
    let mut travel = vec![false; last_day + 1];
    for &day in &days {
        travel[day as usize] = true;
    }
    // cost[d] is the cheapest way to cover every trip on calendar days 1..=d.
    let mut cost = vec![0; last_day + 1];
    for d in 1..=last_day {
        if !travel[d] {
            cost[d] = cost[d - 1];
            continue;
        }
        cost[d] = (cost[d - 1] + costs[0])
            .min(cost[d.saturating_sub(7)] + costs[1])
            .min(cost[d.saturating_sub(30)] + costs[2]);
    }
    cost[last_day]
}
