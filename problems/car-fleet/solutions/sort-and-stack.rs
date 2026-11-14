pub fn car_fleet(target: i32, position: Vec<i32>, speed: Vec<i32>) -> i32 {
    let mut cars: Vec<usize> = (0..position.len()).collect();
    cars.sort_unstable_by_key(|&car| position[car]);
    // Fleets formed so far, from the farthest back (bottom) to the closest to the target (top);
    // their arrival times strictly decrease from bottom to top.
    let mut fleets: Vec<f64> = Vec::new();
    for car in cars {
        let arrival = f64::from(target - position[car]) / f64::from(speed[car]);
        // Every fleet behind this car that would arrive no later catches up with it.
        while fleets.last().is_some_and(|&slowest| slowest <= arrival) {
            fleets.pop();
        }
        fleets.push(arrival);
    }
    fleets.len() as i32
}
