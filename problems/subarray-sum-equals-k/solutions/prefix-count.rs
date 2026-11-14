use std::collections::HashMap;

pub fn subarray_sum(nums: Vec<i32>, k: i32) -> i32 {
    // seen[s] counts the prefixes seen so far whose sum is s; the empty prefix sums to 0.
    let mut seen: HashMap<i32, i32> = HashMap::from([(0, 1)]);
    let mut total = 0;
    let mut count = 0;
    for value in nums {
        total += value;
        // `get` returns None for a missing key, which counts as 0.
        count += seen.get(&(total - k)).copied().unwrap_or(0);
        *seen.entry(total).or_insert(0) += 1;
    }
    count
}
