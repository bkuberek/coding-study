const MOD: i64 = 1_000_000_007;

pub fn sum_subarray_mins(arr: Vec<i32>) -> i32 {
    // ending[i] is the sum of the minimums of the subarrays that end at i.
    let mut ending: Vec<i64> = vec![0; arr.len()];
    // Indexes whose values strictly increase from bottom to top.
    let mut stack: Vec<usize> = Vec::new();
    for (index, &value) in arr.iter().enumerate() {
        while stack.last().is_some_and(|&top| arr[top] >= value) {
            stack.pop();
        }
        ending[index] = match stack.last() {
            // Starts after the previous smaller element have minimum `value`; earlier starts
            // have the same minimums as the subarrays ending at `previous`.
            Some(&previous) => ending[previous] + i64::from(value) * (index - previous) as i64,
            None => i64::from(value) * (index as i64 + 1),
        };
        stack.push(index);
    }
    (ending.iter().sum::<i64>() % MOD) as i32
}
