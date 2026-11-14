// The stub fixes the `&mut Vec<i32>` parameter; the body only needs a slice.
#[allow(clippy::ptr_arg)]
pub fn move_zeroes(nums: &mut Vec<i32>) {
    let mut write = 0;
    for read in 0..nums.len() {
        if nums[read] != 0 {
            nums.swap(write, read);
            write += 1;
        }
    }
}
