pub fn find_peak_element(nums: Vec<i32>) -> i32 {
    // Invariant: some peak of the whole array lies in [low, high].
    let (mut low, mut high) = (0, nums.len() - 1);
    while low < high {
        let middle = low + (high - low) / 2;
        if nums[middle] < nums[middle + 1] {
            low = middle + 1;
        } else {
            high = middle;
        }
    }
    low as i32
}
