const GOOD: i32 = 0;
const BAD: i32 = 1;

pub fn first_bad_commit(statuses: Vec<i32>) -> Vec<i32> {
    let mut last_good: i32 = -1;
    for (position, &status) in statuses.iter().enumerate() {
        if status == GOOD {
            last_good = position as i32;
        } else if status == BAD {
            return vec![last_good + 1, position as i32];
        }
    }
    panic!("the history has no bad commit");
}
