// The stub fixes the `&mut Vec<i32>` parameter; the body only needs a slice.
#[allow(clippy::ptr_arg)]
pub fn sort_colors(nums: &mut Vec<i32>) {
    // `high` is one past the unsorted region, so it never underflows on an empty vector.
    let (mut low, mut mid, mut high) = (0, 0, nums.len());
    while mid < high {
        match nums[mid] {
            0 => {
                nums.swap(low, mid);
                low += 1;
                mid += 1;
            }
            1 => mid += 1,
            _ => {
                high -= 1;
                nums.swap(mid, high);
            }
        }
    }
}
