pub fn can_complete_circuit(gas: Vec<i32>, cost: Vec<i32>) -> i32 {
    // balance is the fuel after driving from station 0 past `station` (it may go negative).
    // Starting right after the station where it is lowest lifts every point of the trip to
    // at least zero, provided the whole circle does not lose fuel.
    let (mut balance, mut lowest, mut start) = (0, 0, 0);
    for station in 0..gas.len() {
        balance += gas[station] - cost[station];
        if balance < lowest {
            lowest = balance;
            start = station + 1;
        }
    }
    if balance < 0 {
        return -1;
    }
    (start % gas.len()) as i32
}
