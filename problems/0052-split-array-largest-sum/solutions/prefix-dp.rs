pub fn split_array(nums: Vec<i32>, k: i32) -> i32 {
    let n = nums.len();
    let mut prefix = vec![0; n + 1];
    for (i, &value) in nums.iter().enumerate() {
        prefix[i + 1] = prefix[i] + value;
    }
    // best[i]: the smallest cost of cutting nums[..i] into the current number of pieces.
    let mut best = prefix.clone();
    for pieces in 2..=k as usize {
        let mut next = vec![0; n + 1];
        for end in pieces..=n {
            next[end] = (pieces - 1..end)
                .map(|cut| best[cut].max(prefix[end] - prefix[cut]))
                .min()
                .unwrap();
        }
        best = next;
    }
    best[n]
}
