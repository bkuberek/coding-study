use std::cmp::Ordering;

pub fn search_range(nums: Vec<i32>, target: i32) -> Vec<i32> {
    // The bounds are signed because `high` is -1 for an empty array and after a miss on the left.
    let (mut low, mut high) = (0, nums.len() as i32 - 1);
    while low <= high {
        let middle = low + (high - low) / 2;
        match nums[middle as usize].cmp(&target) {
            Ordering::Equal => {
                let (mut first, mut last) = (middle as usize, middle as usize);
                while first > 0 && nums[first - 1] == target {
                    first -= 1;
                }
                while last + 1 < nums.len() && nums[last + 1] == target {
                    last += 1;
                }
                return vec![first as i32, last as i32];
            }
            Ordering::Less => low = middle + 1,
            Ordering::Greater => high = middle - 1,
        }
    }
    vec![-1, -1]
}
