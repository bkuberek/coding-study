pub fn longest_consecutive(nums: Vec<i32>) -> i32 {
    let mut longest = 0;
    for (i, &value) in nums.iter().enumerate() {
        if nums.contains(&(value - 1)) {
            continue;
        }
        if nums[..i].contains(&value) {
            continue; // an earlier copy of this start already counted its run
        }
        let mut length = 1;
        while nums.contains(&(value + length)) {
            length += 1;
        }
        longest = longest.max(length);
    }
    longest
}
