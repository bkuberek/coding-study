const MOD: i64 = 1_000_000_007;

pub fn sum_subarray_mins(arr: Vec<i32>) -> i32 {
    let mut total: i64 = 0;
    // Indexes whose values strictly increase from bottom to top.
    let mut stack: Vec<usize> = Vec::new();
    // One extra step with value 0, below every element, pops whatever is left.
    for index in 0..=arr.len() {
        let value = arr.get(index).copied().unwrap_or(0);
        while let Some(&middle) = stack.last() {
            if arr[middle] < value {
                break;
            }
            stack.pop();
            let previous = stack.last().map_or(-1, |&below| below as i64);
            // Starts after the previous strictly smaller element, ends before the next
            // smaller-or-equal one (index): arr[middle] is the minimum of left * right subarrays.
            let left = middle as i64 - previous;
            let right = (index - middle) as i64;
            total += i64::from(arr[middle]) * left * right;
        }
        stack.push(index);
    }
    (total % MOD) as i32
}
