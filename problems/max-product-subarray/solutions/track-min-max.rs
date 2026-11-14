pub fn max_product(nums: Vec<i32>) -> i32 {
    // largest and smallest are the extreme products of subarrays that end at the current index.
    let (mut largest, mut smallest, mut best) = (nums[0], nums[0], nums[0]);
    for &value in &nums[1..] {
        let candidates = [value, largest * value, smallest * value];
        largest = candidates.into_iter().max().unwrap();
        smallest = candidates.into_iter().min().unwrap();
        best = best.max(largest);
    }
    best
}
