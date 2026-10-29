use std::collections::{HashSet, VecDeque};

const START: &str = "0000";

/// The eight settings one move away: each wheel up or down by one, wrapping around.
fn turns(setting: &str) -> Vec<String> {
    let digits = setting.as_bytes();
    let mut result = Vec::with_capacity(8);
    for (wheel, &digit) in digits.iter().enumerate() {
        for turn in [1, 9] {
            let mut following = digits.to_vec();
            following[wheel] = b'0' + (digit - b'0' + turn) % 10;
            result.push(String::from_utf8(following).unwrap());
        }
    }
    result
}

pub fn open_lock(deadends: Vec<String>, target: String) -> i32 {
    // Dead ends behave like settings that were already visited: the search never enters them.
    let mut seen: HashSet<String> = deadends.into_iter().collect();
    if seen.contains(START) {
        return -1;
    }
    seen.insert(START.to_string());
    let mut queue = VecDeque::from([(START.to_string(), 0)]);
    while let Some((setting, moves)) = queue.pop_front() {
        if setting == target {
            return moves;
        }
        for following in turns(&setting) {
            if seen.insert(following.clone()) {
                queue.push_back((following, moves + 1));
            }
        }
    }
    -1
}
