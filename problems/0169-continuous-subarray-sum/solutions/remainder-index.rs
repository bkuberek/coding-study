use std::collections::HashMap;

pub fn check_subarray_sum(nums: Vec<i32>, k: i32) -> bool {
    // `remainder + value` can pass `i32::MAX` (k is up to 2^31 - 1), so the arithmetic is 64-bit.
    let k = i64::from(k);
    // first_index[r] is the earliest position whose prefix (ending there) leaves remainder r;
    // the empty prefix ends at position -1.
    let mut first_index: HashMap<i64, i64> = HashMap::from([(0, -1)]);
    let mut remainder = 0;
    for (position, &value) in nums.iter().enumerate() {
        let position = position as i64;
        remainder = (remainder + i64::from(value)) % k;
        let earlier = *first_index.entry(remainder).or_insert(position);
        if position - earlier >= 2 {
            return true;
        }
    }
    false
}
