pub fn search(nums: Vec<i32>, target: i32) -> i32 {
    // Find the first index whose value is >= target, in the half-open range [low, high).
    let (mut low, mut high) = (0, nums.len());
    while low < high {
        let middle = low + (high - low) / 2;
        if nums[middle] < target {
            low = middle + 1;
        } else {
            high = middle;
        }
    }
    if low < nums.len() && nums[low] == target {
        low as i32
    } else {
        -1
    }
}
