pub fn car_pooling(trips: Vec<Vec<i32>>, capacity: i32) -> bool {
    let mut events = Vec::with_capacity(2 * trips.len());
    for trip in &trips {
        let (passengers, start, end) = (trip[0], trip[1], trip[2]);
        events.push((start, passengers));
        events.push((end, -passengers));
    }
    // Tuples sort by location, then by change: drop-offs (negative) come before pickups.
    events.sort_unstable();
    let mut load = 0;
    for (_, change) in events {
        load += change;
        if load > capacity {
            return false;
        }
    }
    true
}
