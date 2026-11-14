pub fn daily_temperatures(temperatures: Vec<i32>) -> Vec<i32> {
    let mut waits = vec![0; temperatures.len()]; // 0 stays for a day with no warmer day after it
    for (day, &temperature) in temperatures.iter().enumerate() {
        if let Some(offset) = temperatures[day + 1..]
            .iter()
            .position(|&later| later > temperature)
        {
            waits[day] = offset as i32 + 1;
        }
    }
    waits
}
