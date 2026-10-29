use std::collections::HashMap;

pub fn top_k_frequent(nums: Vec<i32>, k: i32) -> Vec<i32> {
    let k = k as usize;
    let n = nums.len();
    let mut counts: HashMap<i32, usize> = HashMap::new();
    for value in nums {
        *counts.entry(value).or_insert(0) += 1;
    }
    // buckets[c] holds the values that occur exactly c times; no count exceeds n.
    let mut buckets: Vec<Vec<i32>> = vec![Vec::new(); n + 1];
    for (value, count) in counts {
        buckets[count].push(value);
    }
    let mut answer = Vec::with_capacity(k);
    for count in (1..=n).rev() {
        for &value in &buckets[count] {
            answer.push(value);
            if answer.len() == k {
                return answer;
            }
        }
    }
    answer
}
