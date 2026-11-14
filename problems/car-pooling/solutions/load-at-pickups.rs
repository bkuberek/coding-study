pub fn car_pooling(trips: Vec<Vec<i32>>, capacity: i32) -> bool {
    // The load is highest right after some pickup, so checking every pickup point suffices.
    let mut busiest = 0;
    for pickup_trip in &trips {
        let pickup = pickup_trip[1];
        let load: i32 = trips
            .iter()
            .filter(|trip| trip[1] <= pickup && pickup < trip[2])
            .map(|trip| trip[0])
            .sum();
        busiest = busiest.max(load);
    }
    busiest <= capacity
}
