pub fn num_of_minutes(n: i32, head_id: i32, manager: Vec<i32>, inform_time: Vec<i32>) -> i32 {
    let mut longest = 0;
    for employee in 0..n {
        // The news reaches employee after every manager above them has passed it on.
        let mut elapsed = 0;
        let mut current = employee;
        while current != head_id {
            current = manager[current as usize];
            elapsed += inform_time[current as usize];
        }
        longest = longest.max(elapsed);
    }
    longest
}
