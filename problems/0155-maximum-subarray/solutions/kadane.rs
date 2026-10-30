pub fn max_sub_array(nums: Vec<i32>) -> i32 {
    // ending_here is the best sum of a subarray that ends at the current index.
    let (mut ending_here, mut best) = (nums[0], nums[0]);
    for &value in &nums[1..] {
        ending_here = value.max(ending_here + value);
        best = best.max(ending_here);
    }
    best
}
