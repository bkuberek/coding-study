pub fn can_complete_circuit(gas: Vec<i32>, cost: Vec<i32>) -> i32 {
    let mut total = 0; // fuel balance of the whole circle
    let mut fuel = 0; // fuel since the current candidate start
    let mut start = 0;
    for station in 0..gas.len() {
        let surplus = gas[station] - cost[station];
        total += surplus;
        fuel += surplus;
        if fuel < 0 {
            // No station from `start` to `station` can be the answer; try the next one.
            start = station + 1;
            fuel = 0;
        }
    }
    if total >= 0 {
        start as i32
    } else {
        -1
    }
}
