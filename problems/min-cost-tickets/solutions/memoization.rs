const DURATIONS: [i32; 3] = [1, 7, 30];

pub fn mincost_tickets(days: Vec<i32>, costs: Vec<i32>) -> i32 {
    // memo[index] is the cheapest cost of covering days[index..], or None while unknown.
    let mut memo = vec![None; days.len()];
    cheapest_from(0, &days, &costs, &mut memo)
}

// A pass bought for days[index] covers through days[index] + duration - 1; this is the
// first trip it leaves uncovered.
fn first_uncovered(index: usize, duration: i32, days: &[i32]) -> usize {
    let mut following = index;
    while following < days.len() && days[following] < days[index] + duration {
        following += 1;
    }
    following
}

fn cheapest_from(index: usize, days: &[i32], costs: &[i32], memo: &mut [Option<i32>]) -> i32 {
    if index == days.len() {
        return 0;
    }
    if let Some(known) = memo[index] {
        return known;
    }
    let mut cheapest = i32::MAX;
    for (&duration, &price) in DURATIONS.iter().zip(costs) {
        let following = first_uncovered(index, duration, days);
        cheapest = cheapest.min(price + cheapest_from(following, days, costs, memo));
    }
    memo[index] = Some(cheapest);
    cheapest
}
