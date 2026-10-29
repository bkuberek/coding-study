pub fn find_min(nums: Vec<i32>) -> i32 {
    // Invariant: the index of the minimum lies in [low, high].
    let (mut low, mut high) = (0, nums.len() - 1);
    while low < high {
        let middle = low + (high - low) / 2;
        if nums[middle] > nums[high] {
            low = middle + 1;
        } else {
            high = middle;
        }
    }
    nums[low]
}
