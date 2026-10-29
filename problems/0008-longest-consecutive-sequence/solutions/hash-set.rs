use std::collections::HashSet;

pub fn longest_consecutive(nums: Vec<i32>) -> i32 {
    let present: HashSet<i32> = nums.into_iter().collect();
    let mut longest = 0;
    for &value in &present {
        if present.contains(&(value - 1)) {
            continue;
        }
        let mut end = value + 1;
        while present.contains(&end) {
            end += 1;
        }
        longest = longest.max(end - value);
    }
    longest
}
