pub fn longest_ones(nums: Vec<i32>, k: i32) -> i32 {
    let (mut left, mut zeros, mut best) = (0, 0, 0);
    for (right, &value) in nums.iter().enumerate() {
        if value == 0 {
            zeros += 1;
        }
        while zeros > k {
            if nums[left] == 0 {
                zeros -= 1;
            }
            left += 1;
        }
        best = best.max(right + 1 - left);
    }
    best as i32
}
