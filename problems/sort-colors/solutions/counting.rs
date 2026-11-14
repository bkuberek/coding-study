// The stub fixes the `&mut Vec<i32>` parameter; the body only needs a slice.
#[allow(clippy::ptr_arg)]
pub fn sort_colors(nums: &mut Vec<i32>) {
    let mut counts = [0usize; 3];
    for &color in nums.iter() {
        counts[color as usize] += 1;
    }
    let mut index = 0;
    for (color, &count) in counts.iter().enumerate() {
        nums[index..index + count].fill(color as i32);
        index += count;
    }
}
