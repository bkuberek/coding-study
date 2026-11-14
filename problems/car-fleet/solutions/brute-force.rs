pub fn car_fleet(target: i32, position: Vec<i32>, speed: Vec<i32>) -> i32 {
    // Arrival times are distance / speed; compare them by cross-multiplying, so no division.
    let distance: Vec<i64> = position
        .iter()
        .map(|&mile| i64::from(target - mile))
        .collect();
    let arrives_later = |car: usize, other: usize| {
        distance[car] * i64::from(speed[other]) > distance[other] * i64::from(speed[car])
    };
    let mut fleets = 0;
    for (car, &mile) in position.iter().enumerate() {
        let mut slowest: Option<usize> = None;
        for (other, &other_mile) in position.iter().enumerate() {
            if other_mile <= mile {
                continue;
            }
            match slowest {
                Some(current) if !arrives_later(other, current) => {}
                _ => slowest = Some(other),
            }
        }
        // The car leads its own fleet only if it arrives strictly later than the slowest car ahead.
        let leads = match slowest {
            Some(ahead) => arrives_later(car, ahead),
            None => true,
        };
        if leads {
            fleets += 1;
        }
    }
    fleets
}
