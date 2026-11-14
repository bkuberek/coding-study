pub fn search_insert(nums: Vec<i32>, target: i32) -> i32 {
    // The answer lies in [low, high]; both are indexes, so they never go below zero.
    let (mut low, mut high) = (0, nums.len());
    while low < high {
        let middle = low + (high - low) / 2;
        if nums[middle] < target {
            low = middle + 1;
        } else {
            high = middle;
        }
    }
    low as i32
}
