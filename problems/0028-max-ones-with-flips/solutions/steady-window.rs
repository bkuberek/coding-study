pub fn longest_ones(nums: Vec<i32>, k: i32) -> i32 {
    let (mut left, mut flips_left) = (0, k);
    for &value in &nums {
        if value == 0 {
            flips_left -= 1;
        }
        if flips_left < 0 {
            if nums[left] == 0 {
                flips_left += 1;
            }
            left += 1;
        }
    }
    (nums.len() - left) as i32
}
