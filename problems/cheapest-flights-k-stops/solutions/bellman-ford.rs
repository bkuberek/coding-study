const UNREACHED: i32 = i32::MAX;

pub fn find_cheapest_price(n: i32, flights: Vec<Vec<i32>>, src: i32, dst: i32, k: i32) -> i32 {
    // price[c] is the cheapest known price to reach c with at most `round` flights.
    let mut price = vec![UNREACHED; n as usize];
    price[src as usize] = 0;
    for _ in 0..=k {
        // Read from the previous round only, so one round never chains two flights.
        let previous = price.clone();
        let mut changed = false;
        for flight in &flights {
            let (start, end, cost) = (flight[0] as usize, flight[1] as usize, flight[2]);
            if previous[start] != UNREACHED && previous[start] + cost < price[end] {
                price[end] = previous[start] + cost;
                changed = true;
            }
        }
        if !changed {
            break;
        }
    }
    match price[dst as usize] {
        UNREACHED => -1,
        cheapest => cheapest,
    }
}
