pub fn min_sub_array_len(target: i32, nums: Vec<i32>) -> i32 {
    let (mut best, mut total, mut left) = (0, 0, 0);
    for (right, &value) in nums.iter().enumerate() {
        total += value;
        while total >= target {
            if best == 0 || right + 1 - left < best {
                best = right + 1 - left;
            }
            total -= nums[left];
            left += 1;
        }
    }
    best as i32
}
