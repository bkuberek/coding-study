pub fn car_pooling(trips: Vec<Vec<i32>>, capacity: i32) -> bool {
    let last = trips.iter().map(|trip| trip[2]).max().unwrap_or(0) as usize;
    // change[x] is how much the load changes at location x; its prefix sums are the loads.
    let mut change = vec![0; last + 1];
    for trip in &trips {
        let (passengers, start, end) = (trip[0], trip[1] as usize, trip[2] as usize);
        change[start] += passengers;
        change[end] -= passengers;
    }
    let mut load = 0;
    for delta in change {
        load += delta;
        if load > capacity {
            return false;
        }
    }
    true
}
