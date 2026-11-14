pub fn longest_consecutive(mut nums: Vec<i32>) -> i32 {
    if nums.is_empty() {
        return 0;
    }
    nums.sort_unstable();
    let mut longest = 1;
    let mut current = 1;
    for pair in nums.windows(2) {
        let (previous, value) = (pair[0], pair[1]);
        if value == previous {
            continue;
        }
        current = if value == previous + 1 {
            current + 1
        } else {
            1
        };
        longest = longest.max(current);
    }
    longest
}
