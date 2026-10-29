use std::cmp::Ordering;

pub fn search(nums: Vec<i32>, target: i32) -> i32 {
    // Invariant: if target is in nums, its index lies in [low, high]. The bounds are signed
    // because `high` reaches -1 when the target is smaller than every element.
    let mut low: i32 = 0;
    let mut high = nums.len() as i32 - 1;
    while low <= high {
        let middle = low + (high - low) / 2;
        match nums[middle as usize].cmp(&target) {
            Ordering::Equal => return middle,
            Ordering::Less => low = middle + 1,
            Ordering::Greater => high = middle - 1,
        }
    }
    -1
}
