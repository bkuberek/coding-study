pub fn daily_temperatures(temperatures: Vec<i32>) -> Vec<i32> {
    let mut waits = vec![0; temperatures.len()];
    // Days still waiting for a warmer day; their readings never rise from bottom to top.
    let mut waiting: Vec<usize> = Vec::new();
    for (day, &temperature) in temperatures.iter().enumerate() {
        while let Some(&earlier) = waiting.last() {
            if temperatures[earlier] >= temperature {
                break;
            }
            waiting.pop();
            waits[earlier] = (day - earlier) as i32;
        }
        waiting.push(day);
    }
    waits
}
