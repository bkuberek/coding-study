use std::cmp::Ordering;

pub fn search(nums: Vec<i32>, target: i32) -> i32 {
    let pivot = index_of_minimum(&nums);
    let last = nums.len() as i32 - 1;
    if nums[pivot as usize] <= target && target <= nums[last as usize] {
        binary_search(&nums, target, pivot, last)
    } else {
        binary_search(&nums, target, 0, pivot - 1)
    }
}

fn index_of_minimum(nums: &[i32]) -> i32 {
    let (mut low, mut high) = (0, nums.len() - 1);
    while low < high {
        let middle = low + (high - low) / 2;
        if nums[middle] > nums[high] {
            low = middle + 1;
        } else {
            high = middle;
        }
    }
    low as i32
}

/// The bounds are signed because `high` is -1 when the target lies before the pivot at index 0.
fn binary_search(nums: &[i32], target: i32, mut low: i32, mut high: i32) -> i32 {
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
