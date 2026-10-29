const WINDOW: usize = 30;

pub fn mincost_tickets(days: Vec<i32>, costs: Vec<i32>) -> i32 {
    // cost[d % WINDOW] holds the cheapest cover of days 1..=d for the last 30 calendar days;
    // nothing older is ever read, because the longest pass lasts 30 days.
    let mut cost = [0; WINDOW];
    let mut next_trip = 0;
    let last_day = days[days.len() - 1] as usize;
    for d in 1..=last_day {
        let previous = cost[(d - 1) % WINDOW];
        if d != days[next_trip] as usize {
            cost[d % WINDOW] = previous;
            continue;
        }
        next_trip += 1;
        let week_ago = if d >= 7 { cost[(d - 7) % WINDOW] } else { 0 };
        let month_ago = if d >= WINDOW { cost[d % WINDOW] } else { 0 };
        cost[d % WINDOW] = (previous + costs[0])
            .min(week_ago + costs[1])
            .min(month_ago + costs[2]);
    }
    cost[last_day % WINDOW]
}
