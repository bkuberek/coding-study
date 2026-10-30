pub fn can_complete_circuit(gas: Vec<i32>, cost: Vec<i32>) -> i32 {
    let n = gas.len();
    for start in 0..n {
        let mut fuel = 0;
        // `all` stops at the first station where the tank runs dry.
        let completed = (0..n).all(|step| {
            let station = (start + step) % n;
            fuel += gas[station] - cost[station];
            fuel >= 0
        });
        if completed {
            return start as i32;
        }
    }
    -1
}
