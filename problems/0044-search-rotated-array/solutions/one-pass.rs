pub fn search(nums: Vec<i32>, target: i32) -> i32 {
    let at = |index: i32| nums[index as usize];
    // The bounds are signed because `high` can reach -1.
    let (mut low, mut high) = (0, nums.len() as i32 - 1);
    while low <= high {
        let middle = low + (high - low) / 2;
        if at(middle) == target {
            return middle;
        }
        if at(low) <= at(middle) {
            // nums[low..=middle] is sorted.
            if (at(low)..at(middle)).contains(&target) {
                high = middle - 1;
            } else {
                low = middle + 1;
            }
        } else if at(middle) < target && target <= at(high) {
            // nums[middle..=high] is sorted and holds the target.
            low = middle + 1;
        } else {
            high = middle - 1;
        }
    }
    -1
}
