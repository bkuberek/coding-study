use std::collections::HashSet;

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
    let blocked: HashSet<String> = deadends.into_iter().collect();
    if blocked.contains(START) {
        return -1;
    }
    if target == START {
        return 0;
    }
    // Two frontiers grow toward each other; moves counts the levels expanded so far.
    let mut near = HashSet::from([START.to_string()]);
    let mut far = HashSet::from([target.clone()]);
    let mut seen = HashSet::from([START.to_string(), target]);
    let mut moves = 0;
    while !near.is_empty() && !far.is_empty() {
        if near.len() > far.len() {
            std::mem::swap(&mut near, &mut far); // always expand the smaller frontier
        }
        moves += 1;
        let mut following_level = HashSet::new();
        for setting in &near {
            for following in turns(setting) {
                if far.contains(&following) {
                    return moves;
                }
                if !seen.contains(&following) && !blocked.contains(&following) {
                    seen.insert(following.clone());
                    following_level.insert(following);
                }
            }
        }
        near = following_level;
    }
    -1
}
