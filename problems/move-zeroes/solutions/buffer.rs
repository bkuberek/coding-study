pub fn move_zeroes(nums: &mut Vec<i32>) {
    let mut buffer: Vec<i32> = nums.iter().copied().filter(|&value| value != 0).collect();
    buffer.resize(nums.len(), 0);
    *nums = buffer;
}
